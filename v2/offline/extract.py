"""Real activations at two read positions, per layer:
  start: Δ = state(task + pages) − state(task) at the assistant-start token (the MVP position);
  end:   Δ = state(task + pages) at the last token of the last tool output − the same task-only state.
G2 picks the position on val (train_probe.py). Split-payload rows carry an earlier page (`prior_outputs`); each page
arrives as its own fetch_page call + tool turn.

Features are cached by content (sha1 of task + pages) in features/<model>/, so a rebuilt dataset only re-runs rows
that changed and a resumed run can never attach features to the wrong row. features/<model>/meta.json holds the
run_meta of the run that filled the cache; a run with another precision is refused instead of mixing the two.
"""
import hashlib
import json
import sys
import time

import numpy as np
import torch

from common import (FETCH_CALL, MAX_OUTPUT_TOKENS, RunMismatch, check_run_meta, load_model, messages, parse, render,
                    run_meta)

CHECKPOINT = 100
POSITIONS = ("start", "end")
PREFIX = {"start": "L", "end": "E"}  # npz array names: L9 = start position, layer 9; E9 = end position


def key(task, output, prior=()):
    parts = [task, *prior, output]  # no prior: same key as the MVP's sha1(task \0 output)
    return hashlib.sha1("\0".join(parts).encode("utf-8")).hexdigest()


def pages(r):
    return list(r.get("prior_outputs", [])) + [r["output"]]


def insertion_reaches_model(rendered, insertion):
    """The insertion must reach the model intact. Llama's template JSON-encodes tool content, so its escaped form counts."""
    return insertion in rendered or json.dumps(insertion, ensure_ascii=False)[1:-1] in rendered


def encode(tok, msgs):
    """Token ids of the rendered prompt + the char offset of each token (to find the last tool-output token)."""
    text = render(tok, msgs)
    enc = tok(text, add_special_tokens=False, return_offsets_mapping=True)
    return text, enc["input_ids"], enc["offset_mapping"]


def end_index(text, offsets, output):
    """Index of the last token of the final tool output inside the rendered prompt."""
    for form in (output, json.dumps(output, ensure_ascii=False)[1:-1]):
        tail = form[-40:]
        at = text.rfind(tail)
        if tail and at >= 0:
            end = at + len(tail)
            return max(i for i, (s, _) in enumerate(offsets) if s < end)
    raise ValueError("tool output not found in the rendered prompt")


def state(tok, model, layers, task, output=None, device=None, prior=(), call=FETCH_CALL):
    """{position: {layer: vector}}; task-only prompts have only the start position."""
    msgs = messages(task, output, call, prior)
    text, ids, offsets = encode(tok, msgs)
    x = torch.tensor([ids], device=device)
    with torch.no_grad():
        hs = model(x, output_hidden_states=True).hidden_states
    out = {"start": {L: hs[L][0, -1].float().cpu().numpy() for L in layers}}  # last token = assistant start
    if output is not None:
        e = end_index(text, offsets, output)
        out["end"] = {L: hs[L][0, e].float().cpu().numpy() for L in layers}
    return out


def delta(full, base, layers):
    """Both positions are measured against the task-only assistant-start state."""
    return {f"{PREFIX[p]}{L}": full[p][L] - base["start"][L] for p in POSITIONS for L in layers}


def load_cache(run):
    path = run.features / "cache.npz"
    if not path.exists():
        return {}
    meta = run.features / "meta.json"
    check_run_meta(json.loads(meta.read_text()) if meta.exists() else None, run, f"{path}")
    z = np.load(path)
    names = [f"{PREFIX[p]}{L}" for p in POSITIONS for L in run.layers]
    have = [n for n in names if n in z.files]
    # An MVP-era cache has only the start position: those rows count as not cached and are re-extracted.
    return {k: {n: z[n][i] for n in have} for i, k in enumerate(z["keys"])} if have == names else {}


def save_cache(run, cache, meta):
    keys = list(cache)
    names = [f"{PREFIX[p]}{L}" for p in POSITIONS for L in run.layers]
    np.savez(run.features / "cache.npz", keys=np.array(keys), **{n: np.stack([cache[k][n] for k in keys]) for n in names})
    (run.features / "meta.json").write_text(json.dumps(meta, indent=2))


def main(argv=None):
    run, _ = parse(argv, __doc__)
    rows = [json.loads(line) for line in (run.data / "rows.jsonl").read_text(encoding="utf-8").splitlines()]
    run.features.mkdir(parents=True, exist_ok=True)
    try:
        cache = load_cache(run)
    except RunMismatch as e:
        sys.exit(f"{e}. Delete {run.features} to start over with this precision.")
    rkey = lambda r: key(r["task"], r["output"], r.get("prior_outputs", ()))  # noqa: E731
    todo = [r for r in rows if rkey(r) not in cache]
    print(f"{len(rows)} rows, {len(rows) - len(todo)} cached, {len(todo)} to extract", flush=True)

    meta_path = run.features / "meta.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else None
    if todo:
        tok, model, device = load_model(run)
        meta = run_meta(run, device)
        base = {}
        t0 = time.time()
        for i, r in enumerate(todo, 1):
            prior = r.get("prior_outputs", ())
            for page in pages(r):
                assert len(tok(page)["input_ids"]) <= MAX_OUTPUT_TOKENS, r["id"]
            rendered = render(tok, messages(r["task"], r["output"], prior=prior))
            for part in r.get("insertion_parts") or ([r["insertion"]] if r["insertion"] else []):
                assert insertion_reaches_model(rendered, part), r["id"]
            if r["task"] not in base:
                base[r["task"]] = state(tok, model, run.layers, r["task"], device=device)
            full = state(tok, model, run.layers, r["task"], r["output"], device=device, prior=prior)
            cache[rkey(r)] = delta(full, base[r["task"]], run.layers)
            if i % CHECKPOINT == 0:
                save_cache(run, cache, meta)
                print(f"{i}/{len(todo)}  {(time.time() - t0) / i:.2f}s/row", flush=True)
        save_cache(run, cache, meta)

    for p in POSITIONS:
        for L in run.layers:
            arr = np.stack([cache[rkey(r)][f"{PREFIX[p]}{L}"] for r in rows]).astype(np.float32)
            assert arr.shape[0] == len(rows) and not np.isnan(arr).any()
            np.save(run.features / (f"delta_L{L}.npy" if p == "start" else f"delta_end_L{L}.npy"), arr)
    (run.features / "ids.json").write_text(json.dumps([r["id"] for r in rows]))
    print(f"done: {len(rows)} rows", file=sys.stderr)


if __name__ == "__main__":
    main()
