"""Real activations. Δ = state(task + page) − state(task) at the assistant-start token, per layer.

Features are cached by content (sha1 of task + page) in features/<model>/, so a rebuilt dataset only re-runs rows
that changed and a resumed run can never attach features to the wrong row. features/<model>/meta.json holds the
run_meta of the run that filled the cache; a run with another precision is refused instead of mixing the two.
"""
import hashlib
import json
import sys
import time

import numpy as np
import torch

from common import (MAX_OUTPUT_TOKENS, RunMismatch, check_run_meta, load_model, messages, parse, prompt_ids, render,
                    run_meta)

CHECKPOINT = 100


def key(task, output):
    return hashlib.sha1((task + "\0" + output).encode("utf-8")).hexdigest()


def insertion_reaches_model(rendered, insertion):
    """The insertion must reach the model intact. Llama's template JSON-encodes tool content, so its escaped form counts."""
    return insertion in rendered or json.dumps(insertion, ensure_ascii=False)[1:-1] in rendered


def state(tok, model, layers, task, output=None, device=None):
    ids = prompt_ids(tok, task, output, device=device)
    with torch.no_grad():
        hs = model(ids, output_hidden_states=True).hidden_states
    return {L: hs[L][0, -1].float().cpu().numpy() for L in layers}  # last token = assistant start


def load_cache(run):
    path = run.features / "cache.npz"
    if not path.exists():
        return {}
    meta = run.features / "meta.json"
    check_run_meta(json.loads(meta.read_text()) if meta.exists() else None, run, f"{path}")
    z = np.load(path)
    return {k: {L: z[f"L{L}"][i] for L in run.layers} for i, k in enumerate(z["keys"])}


def save_cache(run, cache, meta):
    keys = list(cache)
    np.savez(run.features / "cache.npz", keys=np.array(keys),
             **{f"L{L}": np.stack([cache[k][L] for k in keys]) for L in run.layers})
    (run.features / "meta.json").write_text(json.dumps(meta, indent=2))


def main(argv=None):
    run, _ = parse(argv, __doc__)
    rows = [json.loads(line) for line in (run.data / "rows.jsonl").read_text(encoding="utf-8").splitlines()]
    run.features.mkdir(parents=True, exist_ok=True)
    try:
        cache = load_cache(run)
    except RunMismatch as e:
        sys.exit(f"{e}. Delete {run.features} to start over with this precision.")
    todo = [r for r in rows if key(r["task"], r["output"]) not in cache]
    print(f"{len(rows)} rows, {len(rows) - len(todo)} cached, {len(todo)} to extract", flush=True)

    meta_path = run.features / "meta.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else None
    if todo:
        tok, model, device = load_model(run)
        meta = run_meta(run, device)
        base = {}
        t0 = time.time()
        for i, r in enumerate(todo, 1):
            assert len(tok(r["output"])["input_ids"]) <= MAX_OUTPUT_TOKENS, r["id"]
            if r["insertion"]:
                assert insertion_reaches_model(render(tok, messages(r["task"], r["output"])), r["insertion"]), r["id"]
            if r["task"] not in base:
                base[r["task"]] = state(tok, model, run.layers, r["task"], device=device)
            s = state(tok, model, run.layers, r["task"], r["output"], device=device)
            cache[key(r["task"], r["output"])] = {L: s[L] - base[r["task"]][L] for L in run.layers}
            if i % CHECKPOINT == 0:
                save_cache(run, cache, meta)
                print(f"{i}/{len(todo)}  {(time.time() - t0) / i:.2f}s/row", flush=True)
        save_cache(run, cache, meta)

    for L in run.layers:
        arr = np.stack([cache[key(r["task"], r["output"])][L] for r in rows]).astype(np.float32)
        assert arr.shape[0] == len(rows) and not np.isnan(arr).any()
        np.save(run.features / f"delta_L{L}.npy", arr)
    (run.features / "ids.json").write_text(json.dumps([r["id"] for r in rows]))
    print(f"done: {len(rows)} rows", file=sys.stderr)


if __name__ == "__main__":
    main()
