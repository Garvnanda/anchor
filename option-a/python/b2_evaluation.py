"""Evaluate the frozen MVP probe on the original test split in a captured prompt format."""

import hashlib
import json
from collections import Counter

import numpy as np
import torch

from b2_parity import ROOT, prefill_vector


def metrics(labels, scores, threshold):
    positive, negative = scores[labels], scores[~labels]
    comparisons = positive[:, None] - negative[None, :]
    return {"auroc": float(np.mean(comparisons > 0) + 0.5 * np.mean(comparisons == 0)),
            "detected": int(np.sum(positive >= threshold)), "positiveRows": len(positive),
            "falseBlocks": int(np.sum(negative >= threshold)), "negativeRows": len(negative)}


def evaluate(tokenizer, model, experiment, request, request_id, split="test"):
    mvp = ROOT / "mvp/offline"
    dataset = (mvp / "data/rows.jsonl").read_bytes()
    ids = json.loads((mvp / "features/ids.json").read_text(encoding="utf-8"))
    saved = np.load(mvp / "features/delta_L9.npy", mmap_mode="r")
    all_rows = [json.loads(line) for line in dataset.splitlines()]
    if ids != [row["id"] for row in all_rows] or saved.shape != (len(ids), 896):
        raise ValueError("Saved features must match the original dataset row order")
    rows = [(index, row) for index, row in enumerate(all_rows) if row["split"] == split]
    system = [message for message in request["messages"] if message["role"] == "system"]
    assistant = next(message for message in request["messages"] if message["role"] == "assistant")
    tool = next(message for message in request["messages"] if message["role"] == "tool")
    if tool["content"] != "blue":
        raise ValueError("Expected a plain-text blue tool result from the controlled live run")
    tools = request["tools"]

    def encode(task, result=None):
        messages = [*system, {"role": "user", "content": task}]
        if result is not None:
            messages += [assistant, {**tool, "content": result}]
        encoded = tokenizer.apply_chat_template(messages, tools=tools, add_generation_prompt=True,
                                                tokenize=True, return_tensors="pt")
        return encoded if isinstance(encoded, torch.Tensor) else encoded["input_ids"]

    task_ids = {task: encode(task) for task in dict.fromkeys(row["task"] for _, row in rows)}
    full_ids = [encode(row["task"], row["output"]) for _, row in rows]
    sequences = [*task_ids.values(), *full_ids]
    common_length = 0
    for column in zip(*(sequence[0].tolist() for sequence in sequences)):
        if len(set(column)) != 1:
            break
        common_length += 1
    common_length = min(common_length, min(sequence.shape[-1] for sequence in sequences) - 1)
    if common_length <= 0:
        raise ValueError("Expected a shared prompt prefix with a nonempty suffix")

    with torch.inference_mode():
        cached_prefix = model(input_ids=sequences[0][:, :common_length], use_cache=True,
                              logits_to_keep=1).past_key_values

    def vector(sequence):
        with torch.inference_mode():
            try:
                output = model(input_ids=sequence[:, common_length:], past_key_values=cached_prefix,
                               attention_mask=torch.ones_like(sequence), use_cache=True,
                               logits_to_keep=1, output_hidden_states=True)
                return output.hidden_states[9][0, -1].float().cpu().numpy().copy()
            finally:
                appended = cached_prefix.get_seq_length() - common_length
                if appended:
                    cached_prefix.crop(-appended)

    validation_ids = [*task_ids.values(), full_ids[0], full_ids[len(full_ids) // 2], full_ids[-1]]
    max_cache_error = max(float(np.max(np.abs(vector(sequence) - prefill_vector(tokenizer, model, sequence, None))))
                          for sequence in validation_ids)
    if max_cache_error > 1e-5:
        raise ValueError(f"Prefix cache differs from full prefill by {max_cache_error:g}")
    baselines = {task: vector(sequence) for task, sequence in task_ids.items()}
    cases = []
    for (index, row), sequence in zip(rows, full_ids, strict=True):
        comparison = experiment.compare(vector(sequence) - baselines[row["task"]], saved[index])
        cases.append({"id": row["id"], "label": row["label"], "style": row["style"], **comparison})
        if len(cases) % 25 == 0:
            print(json.dumps({"event": "b2_evaluation_progress", "completed": len(cases), "total": len(rows)}), flush=True)
    labels = np.array([case["label"] for case in cases], dtype=bool)
    live_scores = np.array([case["experimentalScore"] for case in cases])
    reference_scores = np.array([case["referenceScore"] for case in cases])
    changes = Counter(case["style"] for case in cases if not case["sameThresholdDecision"])
    return {"event": "b2_evaluation_complete", "sourceRequestId": request_id,
            "datasetSha256": hashlib.sha256(dataset).hexdigest(), "probeHash": experiment.probe_hash,
            "modelRevision": model.config._name_or_path.replace("\\", "/").rsplit("/", 1)[-1],
            "split": split, "sharedPrefixTokens": common_length, "maxPrefixCacheError": max_cache_error,
            "threshold": experiment.threshold, "historical": metrics(labels, reference_scores, experiment.threshold),
            "openCodeFormat": metrics(labels, live_scores, experiment.threshold),
            "decisionChangesByStyle": dict(changes), "cases": cases}
