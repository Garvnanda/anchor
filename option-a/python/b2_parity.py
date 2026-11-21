"""Measure historical probe compatibility for controlled generation captures."""

import hashlib
from itertools import product
import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]


def prefill_vector(tokenizer, model, ids, generation):
    """Read the final prompt token from the prefill that produced generation logits."""
    import torch

    kwargs = {"input_ids": ids, "attention_mask": torch.ones_like(ids)}
    if generation is None:
        with torch.inference_mode():
            states = model(**kwargs, output_hidden_states=True, logits_to_keep=1).hidden_states
    else:
        states = generation.hidden_states[0]
    if states[9].shape != (1, ids.shape[-1], 896):
        raise ValueError("Unexpected layer-9 prefill shape")
    return states[9][0, -1].float().cpu().numpy().copy()


class ParityExperiment:
    def __init__(self):
        probe = (ROOT / "v2/offline/out/qwen0.5b/probe.json").read_bytes()
        self.probe_hash = hashlib.sha256(probe).hexdigest()
        self.feature_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        metadata = json.loads(probe)
        self.mean, self.scale, self.coef = (np.array(metadata[k]) for k in ("mean", "scale", "coef"))
        self.intercept = metadata["intercept"]
        self.threshold = metadata["threshold"]
        self.initial = None

    def score(self, features):
        logit = ((features - self.mean) / self.scale) @ self.coef + self.intercept
        return float(np.exp(-np.logaddexp(0, -logit)))

    def compare(self, actual, reference):
        difference = actual - reference
        actual_score, reference_score = self.score(actual), self.score(reference)
        return {"maxAbsoluteFeatureDifference": float(np.max(np.abs(difference))),
                "featureRmse": float(np.sqrt(np.mean(difference ** 2))),
                "scoreAbsoluteDifference": abs(actual_score - reference_score),
                "experimentalScore": actual_score, "referenceScore": reference_score,
                "sameThresholdDecision": (actual_score >= self.threshold) == (reference_score >= self.threshold)}

    def observe(self, request_id, request, vector, outgoing_ids, reference, isolation=None):
        messages = request["messages"]
        tool_ids = [m.get("tool_call_id") for m in messages if m["role"] == "tool"]
        prefix = [m for m in messages if m["role"] in {"system", "user"}]
        evidence = {"event": "b2_prefill", "requestId": request_id, "layer": 9,
                    "probeHash": self.probe_hash, "featureExtractionHash": self.feature_hash}
        if not tool_ids and outgoing_ids and self.initial is None:
            self.initial = (request_id, prefix, request.get("tools", []), outgoing_ids, vector)
            return {**evidence, "outcome": "baseline"}
        if self.initial is None:
            return {**evidence, "outcome": "missing_baseline"}
        baseline_id, original_prefix, original_tools, expected_ids, baseline = self.initial
        if (prefix != original_prefix or request.get("tools", []) != original_tools
                or len(tool_ids) != len(set(tool_ids)) or set(tool_ids) != set(expected_ids)):
            return {**evidence, "outcome": "unmatched_context"}
        delta = vector - baseline
        evidence.update(baselineRequestId=baseline_id, toolCallIds=tool_ids)
        if len(tool_ids) == 1:
            historical = reference(messages)
            result = {**evidence, "outcome": "single_result_comparison", **self.compare(delta, historical)}
            if isolation is not None:
                result["promptIsolation"] = isolation(request, historical, delta)
            return result
        return {**evidence, "outcome": "multi_result_aggregate_only",
                "experimentalAggregateScore": self.score(delta), "deltaL2": float(np.linalg.norm(delta))}


def historical_reference(tokenizer, model, messages):
    """Run the historical prompt format as a diagnostic reference only."""
    from common import prompt_ids

    task = next(message["content"] for message in messages if message["role"] == "user")
    result = next(message["content"] for message in messages if message["role"] == "tool")
    base = prefill_vector(tokenizer, model, prompt_ids(tokenizer, task), None)
    full = prefill_vector(tokenizer, model, prompt_ids(tokenizer, task, result), None)
    return full - base


def isolate_prompt(tokenizer, model, experiment, request, historical, live):
    """Use offline forwards to measure prompt differences, including interactions."""
    from common import FETCH_CALL, SYSTEM

    messages = request["messages"]
    user = next(message for message in messages if message["role"] == "user")
    assistant = next(message for message in messages if message["role"] == "assistant")
    result = next(message for message in messages if message["role"] == "tool")
    live_system = [message for message in messages if message["role"] == "system"]
    historical_system = [{"role": "system", "content": SYSTEM}]
    measurements = []

    def encode(prompt, tools):
        tokens = tokenizer.apply_chat_template(prompt, tools=tools, add_generation_prompt=True,
                                               tokenize=True, return_tensors="pt")
        return tokens["input_ids"] if hasattr(tokens, "keys") else tokens

    for system, schemas in product((False, True), repeat=2):
        prefix = [*(live_system if system else historical_system), user]
        definitions = request.get("tools", []) if schemas else []
        base_ids = encode(prefix, definitions)
        base = prefill_vector(tokenizer, model, base_ids, None)
        for call in (False, True):
            full_ids = encode([*prefix, assistant if call else FETCH_CALL, result], definitions)
            delta = prefill_vector(tokenizer, model, full_ids, None) - base
            measurements.append({"liveSystem": system, "liveToolDefinitions": schemas, "liveToolCall": call,
                                 "baselineTokens": base_ids.shape[-1], "continuationTokens": full_ids.shape[-1],
                                 **experiment.compare(delta, historical),
                                 "maxAbsoluteDifferenceFromLive": float(np.max(np.abs(delta - live)))})
    return measurements


def verify_saved_fixture(tokenizer, model, experiment):
    """Isolate the capture method with the exact historical prompt and saved row."""
    import torch
    from common import prompt_ids

    offline = ROOT / "mvp/offline"
    rows = (json.loads(line) for line in (offline / "data/rows.jsonl").read_text(encoding="utf-8").splitlines())
    row = next(row for row in rows if row["split"] == "test")
    index = json.loads((offline / "features/ids.json").read_text()).index(row["id"])
    saved = np.load(offline / "features/delta_L9.npy", mmap_mode="r")[index]
    vectors = []
    for result in (None, row["output"]):
        ids = prompt_ids(tokenizer, row["task"], result)
        with torch.inference_mode():
            generated = model.generate(input_ids=ids, attention_mask=torch.ones_like(ids), max_new_tokens=1,
                                       do_sample=False, return_dict_in_generate=True, output_hidden_states=True)
        vectors.append(prefill_vector(tokenizer, model, ids, generated))
    return {"event": "b2_saved_fixture", "rowId": row["id"], **experiment.compare(vectors[1] - vectors[0], saved)}
