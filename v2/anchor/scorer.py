"""Live Anchor scorer: model + probe loaded once; drift score for a tool output given the task and the run's
earlier tool outputs; fail closed.

Δ is computed exactly as in training (offline/extract.py): state(task + every page so far) − state(task) at the
probe's read position and layer, so a split payload is scored with its earlier half in context. Long outputs
(over the 400-token training budget) are scored as their first and last 400 tokens and the max is taken;
empty outputs are not scored (clean, `skipped`). Any error or timeout returns a fail-closed result: tainted, with
the reason, so the pending side effect is blocked.
"""
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from pathlib import Path

import numpy as np

OFFLINE = Path(__file__).resolve().parents[1] / "offline"
if str(OFFLINE) not in sys.path:
    sys.path.insert(0, str(OFFLINE))

import extract  # noqa: E402
from common import MAX_OUTPUT_TOKENS, load_model, load_probe  # noqa: E402

TIMEOUT_S = 30.0
PROBE_VERSION = "v2"
SENTENCE = re.compile(r"[^.!?\n]+(?:[.!?]+|\n|$)")


def sentences(text):
    """(start, end) character spans of the sentences in text; spans always index the caller's own string."""
    spans = []
    for m in SENTENCE.finditer(text):
        s, e = m.start(), m.end()
        while s < e and text[s].isspace():
            s += 1
        while e > s and text[e - 1].isspace():
            e -= 1
        if e > s:
            spans.append((s, e))
    return spans


class Scorer:
    def __init__(self, run, tok=None, model=None, device=None, timeout_s=TIMEOUT_S):
        self.run = run
        self.probe = load_probe(run)  # refuses a probe of another model / precision
        self.layer = self.probe["layer"]
        self.position = self.probe.get("position", "start")
        self.threshold = self.probe["threshold"]
        self.mean, self.scale = np.array(self.probe["mean"]), np.array(self.probe["scale"])
        self.coef, self.intercept = np.array(self.probe["coef"]), self.probe["intercept"]
        if model is None:
            tok, model, device = load_model(run)
        self.tok, self.model, self.device = tok, model, device
        self.timeout_s = timeout_s
        self.lock = threading.Lock()  # one forward pass at a time: requests queue
        self.base = {}  # task -> task-only state (cached per task, as in training)
        self.pool = ThreadPoolExecutor(max_workers=1)

    # --- core ------------------------------------------------------------------------------------------------------

    def _prob(self, delta):
        z = ((delta - self.mean) / self.scale) @ self.coef + self.intercept
        return float(1 / (1 + np.exp(-z)))

    def _base(self, task):
        if task not in self.base:
            self.base[task] = extract.state(self.tok, self.model, [self.layer], task, device=self.device)["start"][self.layer]
        return self.base[task]

    def _delta(self, task, output, prior):
        full = extract.state(self.tok, self.model, [self.layer], task, output, device=self.device, prior=tuple(prior))
        return full[self.position][self.layer] - self._base(task)

    def _windows(self, output):
        """The output itself, or its first and last MAX_OUTPUT_TOKENS tokens when it is longer (truncated=True)."""
        ids = self.tok(output, add_special_tokens=False)["input_ids"]
        if len(ids) <= MAX_OUTPUT_TOKENS:
            return [output], False
        return [self.tok.decode(ids[:MAX_OUTPUT_TOKENS]), self.tok.decode(ids[-MAX_OUTPUT_TOKENS:])], True

    def raw_score(self, task, output, prior=()):
        if not output.strip():
            return {"drift_score": 0.0, "skipped": True, "truncated": False}
        windows, truncated = self._windows(output)
        prior = [w for p in prior for w in self._windows(p)[0][-1:]]  # earlier pages: their last window
        score = max(round(self._prob(self._delta(task, w, prior)), 6) for w in windows)
        return {"drift_score": score, "skipped": False, "truncated": truncated}

    # --- attribution -------------------------------------------------------------------------------------------------

    def leave_one_out(self, task, output, prior=()):
        """Per sentence: score(full) − score(without that sentence). Spans index `output`."""
        full = self.raw_score(task, output, prior)["drift_score"]
        out = []
        for s, e in sentences(output):
            rest = (output[:s] + output[e:]).strip()
            out.append({"start": s, "end": e, "text": output[s:e],
                        "weight": round(full - self.raw_score(task, rest, prior)["drift_score"], 6)})
        return out

    def projection(self, task, output, prior=()):
        """One pass: per-token states at the probe layer projected on the probe direction, averaged per sentence."""
        import torch

        msgs = extract.messages(task, output, extract.FETCH_CALL, tuple(prior))
        text, ids, offsets = extract.encode(self.tok, msgs)
        with torch.no_grad():
            hs = self.model(torch.tensor([ids], device=self.device), output_hidden_states=True).hidden_states
        states = hs[self.layer][0].float().cpu().numpy()
        w = self.coef / self.scale
        proj = (states - self.mean) @ w
        at = text.rfind(output) if output in text else None
        out = []
        for s, e in sentences(output):
            if at is None:  # Llama JSON-escapes tool content: fall back to equal weights rather than guess offsets
                weight = 0.0
            else:
                toks = [i for i, (a, b) in enumerate(offsets) if a >= at + s and b <= at + e and b > a]
                weight = float(proj[toks].mean()) if toks else 0.0
            out.append({"start": s, "end": e, "text": output[s:e], "weight": round(weight, 6)})
        return out

    # --- fail-closed entry point ------------------------------------------------------------------------------------------

    def score(self, task, output, prior=(), attribution=None):
        """Never raises. Error or timeout → fail-closed result (tainted, reason)."""
        t0 = time.perf_counter()

        def work():
            with self.lock:
                r = self.raw_score(task, output, prior)
                if attribution and not r["skipped"]:
                    r["attribution"] = getattr(self, attribution)(task, output, prior)
                return r

        try:
            r = self.pool.submit(work).result(timeout=self.timeout_s)
            r.update(tainted=r["drift_score"] >= self.threshold, fail_closed=False)
        except FutureTimeout:
            r = {"drift_score": None, "tainted": True, "fail_closed": True, "reason": f"scorer timeout ({self.timeout_s:g} s)"}
        except Exception as e:  # noqa: BLE001 — any scorer failure blocks the side effect
            r = {"drift_score": None, "tainted": True, "fail_closed": True, "reason": f"scorer error: {type(e).__name__}"}
        r.update(threshold=self.threshold, layer=self.layer, position=self.position, probe_version=PROBE_VERSION,
                 run_meta=self.probe["run_meta"], latency_ms=round((time.perf_counter() - t0) * 1000, 1))
        return r
