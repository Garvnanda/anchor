"""Compare the managed provider's real prefill and the historical MVP extractor."""
import json
import os
from pathlib import Path
import sys

import numpy as np
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

root = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(root / "option-a/python"), str(root / "mvp/offline")]
from b1_provider import generate, REVISION
from common import messages
from extract import state


def first_forward(model, operation):
    tokens = []
    def record(_, args, kwargs):
        if not tokens:
            ids = kwargs["input_ids"] if "input_ids" in kwargs else args[0]
            tokens.append(ids.detach().clone())
    hook = model.register_forward_pre_hook(record, with_kwargs=True)
    try:
        value = operation()
    finally:
        hook.remove()
    return tokens[0], value


def main():
    torch.set_num_threads(max(1, (os.cpu_count() or 2) // 2))
    snapshot = Path.home()/".cache/huggingface/hub/models--Qwen--Qwen2.5-0.5B-Instruct/snapshots"/REVISION
    tokenizer = AutoTokenizer.from_pretrained(snapshot, local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(snapshot, dtype=torch.float32, local_files_only=True).eval()
    rows = [json.loads(line) for line in (root/"mvp/offline/data/rows.jsonl").read_text(encoding="utf8").splitlines()]
    for label in (0, 1):
        row = next(r for r in rows if r["split"] == "test" and r["label"] == label)
        pairs = []
        for output in (None, row["output"]):
            expected_ids, expected = first_forward(model, lambda: state(tokenizer, model, row["task"], output)[9])
            request = {"messages": messages(row["task"], output)}
            actual_ids, actual = first_forward(model, lambda: generate(tokenizer, model, request, capture=True)[3])
            assert torch.equal(actual_ids, expected_ids), row["id"]
            np.testing.assert_array_equal(actual, expected)
            pairs.append((actual, expected))
        diff = (pairs[1][0] - pairs[0][0]) - (pairs[1][1] - pairs[0][1])
        assert np.max(np.abs(diff)) == 0
        print(row["id"], "identical tokens, task and continuation states, and layer-9 delta", flush=True)


if __name__ == "__main__":
    main()
