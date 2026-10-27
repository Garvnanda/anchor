"""Phase 2: real activations. Δ = state(task + page) − state(task) at the assistant-start token, per layer.

Features are cached by content (sha1 of task + page), so a rebuilt dataset only re-runs rows that changed and a
resumed run can never attach features to the wrong row.
"""
import hashlib
import json
import sys
import time

import numpy as np
import torch

from common import DATA, FEATURES, LAYERS, MAX_OUTPUT_TOKENS, load_model, messages, prompt_ids

CHECKPOINT = 100
CACHE = FEATURES / "cache.npz"


def key(task, output):
    return hashlib.sha1((task + "\0" + output).encode("utf-8")).hexdigest()


def state(tok, model, task, output=None):
    ids = prompt_ids(tok, task, output)
    with torch.no_grad():
        hs = model(ids, output_hidden_states=True).hidden_states
    return {L: hs[L][0, -1].float().numpy() for L in LAYERS}  # last token = assistant start


def load_cache():
    if not CACHE.exists():
        return {}
    z = np.load(CACHE)
    return {k: {L: z[f"L{L}"][i] for L in LAYERS} for i, k in enumerate(z["keys"])}


def save_cache(cache):
    keys = list(cache)
    np.savez(CACHE, keys=np.array(keys), **{f"L{L}": np.stack([cache[k][L] for k in keys]) for L in LAYERS})


def main():
    rows = [json.loads(line) for line in (DATA / "rows.jsonl").read_text(encoding="utf-8").splitlines()]
    FEATURES.mkdir(exist_ok=True)
    cache = load_cache()
    todo = [r for r in rows if key(r["task"], r["output"]) not in cache]
    print(f"{len(rows)} rows, {len(rows) - len(todo)} cached, {len(todo)} to extract", flush=True)

    if todo:
        tok, model = load_model()
        base = {}
        t0 = time.time()
        for i, r in enumerate(todo, 1):
            assert len(tok(r["output"])["input_ids"]) <= MAX_OUTPUT_TOKENS, r["id"]
            if r["insertion"]:  # the insertion must reach the model intact
                rendered = tok.apply_chat_template(messages(r["task"], r["output"]), add_generation_prompt=True, tokenize=False)
                assert r["insertion"] in rendered, r["id"]
            if r["task"] not in base:
                base[r["task"]] = state(tok, model, r["task"])
            s = state(tok, model, r["task"], r["output"])
            cache[key(r["task"], r["output"])] = {L: s[L] - base[r["task"]][L] for L in LAYERS}
            if i % CHECKPOINT == 0:
                save_cache(cache)
                print(f"{i}/{len(todo)}  {(time.time() - t0) / i:.2f}s/row", flush=True)
        save_cache(cache)

    for L in LAYERS:
        arr = np.stack([cache[key(r["task"], r["output"])][L] for r in rows]).astype(np.float32)
        assert arr.shape[0] == len(rows) and not np.isnan(arr).any()
        np.save(FEATURES / f"delta_L{L}.npy", arr)
    (FEATURES / "ids.json").write_text(json.dumps([r["id"] for r in rows]))
    print(f"done: {len(rows)} rows", file=sys.stderr)


if __name__ == "__main__":
    main()
