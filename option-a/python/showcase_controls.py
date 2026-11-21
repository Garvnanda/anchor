"""Measure the pinned probe on two held-out controls using real generation prefills."""
import hashlib
import json
import os
from pathlib import Path
import time
import sys
import numpy as np
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from b1_provider import MODEL, REVISION
from b2_parity import prefill_vector
from common import messages

def main():
    assets = Path(__file__).parent
    probe_bytes = (assets / "probe.json").read_bytes()
    if hashlib.sha256(probe_bytes).hexdigest() != "6654792a7a27ee9ea700578842d6a8b3668313bdcef91e55473fe5afe8fd938a":
        raise ValueError("Unexpected probe")
    probe = json.loads(probe_bytes)
    snapshot = Path.home()/".cache/huggingface/hub/models--Qwen--Qwen2.5-0.5B-Instruct/snapshots"/REVISION
    torch.set_num_threads(max(1, (os.cpu_count() or 2)//2))
    tokenizer = AutoTokenizer.from_pretrained(snapshot, local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(snapshot, dtype=torch.float32, local_files_only=True).eval()
    for row in json.loads((assets/"controls.json").read_text(encoding="utf8")):
        wire = "--wire" in sys.argv
        provenance = {"modelId":MODEL,"modelRevision":REVISION,"layer":9,"precision":"fp32",
            "provenanceType":"generation_forward_pass","probeHash":hashlib.sha256(probe_bytes).hexdigest(),
            "featureExtractionHash":hashlib.sha256((assets/"b2_parity.py").read_bytes()).hexdigest()}
        if wire:
            print(json.dumps({"provenance":provenance,"threshold":probe["threshold"]}),flush=True)
            identity = json.loads(sys.stdin.readline())
        started = time.monotonic()
        states = []
        for output in [None, row["output"]]:
            ids = tokenizer.apply_chat_template(messages(row["task"],output), add_generation_prompt=True,
                                                tokenize=True, return_tensors="pt")
            if not isinstance(ids, torch.Tensor):
                ids = ids["input_ids"]
            with torch.inference_mode():
                gen = model.generate(input_ids=ids, attention_mask=torch.ones_like(ids), do_sample=False,
                    max_new_tokens=1, return_dict_in_generate=True, output_hidden_states=True)
            states.append(prefill_vector(tokenizer, model, ids, gen))
        normalized = (states[1]-states[0]-np.array(probe["mean"]))/np.array(probe["scale"])
        score = float(np.exp(-np.logaddexp(0, -(normalized @ probe["coef"] + probe["intercept"]))))
        if wire:
            evidence = {**identity,"schemaVersion":1,"detectorMode":"direct_managed_qwen","status":"ready",
                "score":score,"threshold":probe["threshold"],"provenance":provenance,"errorCode":None,
                "latencyMs":round((time.monotonic()-started)*1000)}
            print(json.dumps({"control":row["id"],"evidence":evidence}),flush=True)
            continue
        print(json.dumps({"profile":"historical matched tokens","control":row["id"], "label":row["label"],
            "score":score,"threshold":probe["threshold"],"flagged":score>=probe["threshold"],
            "elapsedMs":round((time.monotonic()-started)*1000)}),flush=True)
if __name__=="__main__":
    main()
