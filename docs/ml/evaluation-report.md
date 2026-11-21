# Evaluation and resource evidence

The machine-readable companion files record aggregate counts, split identifiers, artifact hashes and cache verification errors. The evaluation holds the original threshold and probe fixed. It renders the existing labeled rows using a prompt format captured from a real local OpenCode tool round trip. Dataset scores come from offline forwards. Live same-generation capture and its limits are documented in [the parity report](parity-report.md).

## Original test split

The 205-row original test split contained 132 positive and 73 negative examples. The OpenCode format yielded 37 true positives and eight false positives, compared with 127 and one in the historical format. AUROC fell from 0.9979 to 0.7858. With the measured scores held fixed, sweeping every distinct cutoff yielded at most 22 detections at a budget of one false positive. This is a retrospective feasibility bound. It rules out recovering the historical operating point on this split by changing the threshold alone. No cutoff was selected from these results.

## Held-out Hindi and Hinglish split

All 44 original held-out rows were scored after fixing the test procedure. Under the observed OpenCode format, the detector caught 9/22 labeled injections and flagged 3/22 benign examples. The historical features yielded 12/22 detections and 2/22 benign flags. AUROC was 0.7459 in the OpenCode format and 0.9339 in the historical format. The maximum prefix-cache check error was 0.00000430. See the [machine-readable results](b6-evaluation.json) for both splits.

## Runtime evidence

The two-call CPU FP32 smoke on Windows x64 used the RTX-equipped audit machine's CPU. Both real no-argument tool calls completed in one scenario and returned matching IDs. The measured turns took 26.07 and 25.76 seconds. The single-result parity run had a sampled peak process working set of approximately 3.21 GiB. These individual observations do not establish latency percentiles. End-to-end enforcement latency and timeout behavior depend on C1.

## Reproduce

```powershell
node option-a/python/b1_smoke.mjs --parity-single --evaluate
node option-a/python/b1_smoke.mjs --parity-single --evaluate --heldout
```

Each run emits a local evidence directory. The raw provider JSON records each row ID, reference score, measured score and threshold agreement. Keep this diagnostic output out of the live event stream.
