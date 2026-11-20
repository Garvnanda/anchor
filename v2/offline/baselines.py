"""H2: baseline detectors on the probe's own rows and splits → out/<model>/baselines.json (+ per-row
baseline_scores.json).

Every detector scores every row (all pages of a split-payload row joined); thresholds come from val only, at 5 % and
1 % FPR (same rule as train_probe.threshold_at_fpr); metrics per split and per attack family use the probe's own
`evaluate`, so the numbers sit side by side with Anchor's.

Detectors (scope, user 2026-10-30): keyword list (MVP), length+position-only control (is the probe cheating?),
Pipelock v3.7.1 response scanner (`pipelock mcp scan`, unmodified binary, balanced preset), Prompt Guard 2 22M / 86M
(gated; pinned revisions). `--detectors` picks a subset, e.g. while Prompt Guard access is pending.
"""
import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path

import numpy as np

from common import load_env, parse, run_meta
from templates import keyword_hit
from train_probe import STRICT_FPR, TARGET_FPR, evaluate, rate, threshold_at_fpr

PIPELOCK = Path(os.environ.get("PIPELOCK", Path.home() / "tools" / "pipelock" / "pipelock.exe"))
PROMPT_GUARD = {  # revision = HF commit, pinned 2026-10-30
    "prompt_guard2_22m": ("meta-llama/Llama-Prompt-Guard-2-22M", "11614a155199674a0a95e6602d6ab0417b790ed0"),
    "prompt_guard2_86m": ("meta-llama/Llama-Prompt-Guard-2-86M", "a8ded8e697ce7c355e395a0df51f94adb4a2fd27"),
}
INFO = {
    "keyword": {"licence": "ours (MVP keyword list)", "revision": "templates.KEYWORDS", "training_overlap": "none"},
    "length_position": {"licence": "ours", "revision": "logistic regression on length / position / format only",
                        "training_overlap": "trained on our train split (it is a control)"},
    "pipelock": {"licence": "core Apache-2.0 (bundled LICENSE); enterprise parts ELv2, not used", "revision": "v3.7.1",
                 "training_overlap": "none (regex rules)"},
    "prompt_guard2_22m": {"licence": "gated; read from the model card when access is granted", "revision": PROMPT_GUARD["prompt_guard2_22m"][1],
                          "training_overlap": "unknown (Meta does not publish the training set)"},
    "prompt_guard2_86m": {"licence": "gated; read from the model card when access is granted", "revision": PROMPT_GUARD["prompt_guard2_86m"][1],
                          "training_overlap": "unknown (Meta does not publish the training set)"},
}
ALL = list(INFO)


def text_of(r):
    return "\n\n".join(r.get("prior_outputs", []) + [r["output"]])


# --- detectors: each returns one score per row (higher = more likely injected) ------------------------------------

def score_keyword(rows):
    return np.array([float(keyword_hit(text_of(r))) for r in rows])


def length_features(r):
    pos = r["position"] or "none"
    t = text_of(r)
    return [len(t), len(t.split()), r["n_tokens"], len(r.get("prior_outputs", [])) + 1, t.lstrip().startswith("{"),
            pos == "start", pos == "middle", pos == "end", pos == "none"]


def score_length_position(rows, train_idx):
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    X = np.array([length_features(r) for r in rows], dtype=float)
    y = np.array([r["label"] for r in rows])
    scaler = StandardScaler().fit(X[train_idx])
    clf = LogisticRegression(max_iter=2000).fit(scaler.transform(X[train_idx]), y[train_idx])
    return clf.predict_proba(scaler.transform(X))[:, 1]


def pipelock_config():
    cfg = Path(tempfile.mkdtemp()) / "pipelock.yaml"
    subprocess.run([str(PIPELOCK), "generate", "config", "--preset", "balanced", "--output", str(cfg)],
                   check=True, capture_output=True)
    return cfg


def score_pipelock(rows):
    """Number of response-scanner matches per row (0 = clean), from the unmodified binary."""
    cfg = pipelock_config()
    lines = "".join(json.dumps({"jsonrpc": "2.0", "id": i, "result": {"content": [{"type": "text", "text": text_of(r)}]}})
                    + "\n" for i, r in enumerate(rows))
    res = subprocess.run([str(PIPELOCK), "mcp", "scan", "--json", "--config", str(cfg)], input=lines,
                         capture_output=True, text=True, encoding="utf-8")
    if res.returncode not in (0, 1):  # 1 = findings present
        raise RuntimeError(f"pipelock mcp scan failed: {res.stderr[-500:]}")
    found = {}
    for line in res.stdout.splitlines():
        if line.startswith("{"):
            v = json.loads(line)
            found[v["id"]] = 0 if v["clean"] else len(v.get("matches", [])) or 1
    assert len(found) == len(rows), f"pipelock scored {len(found)} of {len(rows)} rows"
    INFO["pipelock"]["config_sha256"] = hashlib.sha256(cfg.read_bytes()).hexdigest()
    return np.array([float(found[i]) for i in range(len(rows))])


def score_prompt_guard(rows, name, batch=16):
    """P(malicious), as the model card documents; texts longer than 512 tokens: max over 512-token windows."""
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    load_env()
    repo, rev = PROMPT_GUARD[name]
    tok = AutoTokenizer.from_pretrained(repo, revision=rev, token=os.environ.get("HF_TOKEN"))
    model = AutoModelForSequenceClassification.from_pretrained(repo, revision=rev, token=os.environ.get("HF_TOKEN")).eval()
    windows, owner = [], []
    for i, r in enumerate(rows):
        ids = tok(text_of(r), add_special_tokens=False)["input_ids"]
        for s in range(0, max(len(ids), 1), 510):
            windows.append(tok.decode(ids[s:s + 510]))
            owner.append(i)
    probs = []
    with torch.no_grad():
        for s in range(0, len(windows), batch):
            enc = tok(windows[s:s + batch], truncation=True, max_length=512, padding=True, return_tensors="pt")
            probs += torch.softmax(model(**enc).logits, dim=-1)[:, 1].tolist()
    out = np.zeros(len(rows))
    for i, p in zip(owner, probs):
        out[i] = max(out[i], p)
    return out


# --- evaluation ---------------------------------------------------------------------------------------------------

NATIVE = {"keyword": 0.5, "pipelock": 1.0}  # the detector's own rule: a keyword hit / pipelock "not clean"


def report(rows, scores, y, idx, native=None):
    tr, va, te, ho = idx
    scores = np.round(scores, 6)
    out = {"thresholds": {}}
    if native is not None:  # binary detectors: also their built-in decision, no tuning (comparable with the MVP)
        block = scores >= native
        out["native"] = {"threshold": native, "val_fpr": rate(block[va][y[va] == 0].sum(), (y[va] == 0).sum()),
                         "test": evaluate(rows, te, scores, block), "heldout": evaluate(rows, ho, scores, block)}
    for tag, fpr in (("fpr_0.05", TARGET_FPR), ("fpr_0.01", STRICT_FPR)):
        thr = threshold_at_fpr(scores[va], y[va], fpr)
        block = scores >= thr
        out["thresholds"][tag] = round(thr, 6)
        out[tag] = {"val_fpr": rate(block[va][y[va] == 0].sum(), (y[va] == 0).sum()),
                    "test": evaluate(rows, te, scores, block), "heldout": evaluate(rows, ho, scores, block)}
    return out


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--detectors", default=",".join(ALL), help=f"comma list from {ALL}")
    run, args = parse(argv, parser=p)
    names = args.detectors.split(",")
    assert set(names) <= set(ALL), names
    rows = [json.loads(line) for line in (run.data / "rows.jsonl").read_text(encoding="utf-8").splitlines()]
    y = np.array([r["label"] for r in rows])
    split = np.array([r["split"] for r in rows])
    idx = tuple(np.where(split == s)[0] for s in ("train", "val", "test", "heldout"))

    path, spath = run.out / "baselines.json", run.out / "baseline_scores.json"
    result = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"detectors": {}}
    per_row = json.loads(spath.read_text(encoding="utf-8")) if spath.exists() else {"scores": {}}
    result["run_meta"] = run_meta(run)  # rows are this model's (token budget); the detectors are not
    for name in names:
        if name == "keyword":
            s = score_keyword(rows)
        elif name == "length_position":
            s = score_length_position(rows, idx[0])
        elif name == "pipelock":
            s = score_pipelock(rows)
        else:
            s = score_prompt_guard(rows, name)
        per_row["scores"][name] = {r["id"]: round(float(v), 6) for r, v in zip(rows, s)}
        result["detectors"][name] = {**INFO[name], **report(rows, s, y, idx, NATIVE.get(name)),
                                     "scores_sha256": hashlib.sha256(np.round(s, 6).tobytes()).hexdigest()}
        t = result["detectors"][name]["fpr_0.05"]["test"]
        print(f"{name}: test AUROC {t['auroc']} TPR@5% {t['tpr']['hits']}/{t['tpr']['n']}", flush=True)
    run.out.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    per_row["run_meta"] = result["run_meta"]
    spath.write_text(json.dumps(per_row), encoding="utf-8")


if __name__ == "__main__":
    main()
