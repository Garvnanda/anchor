# Developer B status

## B0 — PASS

The Option A target is managed Qwen generation serving OpenCode, with detector evidence captured from that generation path. The [probe audit](../ml/probe-provenance.md) and [inference audit](../ml/inference-feasibility.md) record the implemented historical path and the remaining evidence gaps.

Validated the local model snapshot and artifact hashes, compared probe parameters and cached feature hashes, counted dataset splits, and inspected local runtimes and tracked source. With owner approval, tested the cached snapshot offline in CPU FP32 against 12 historical MVP rows spanning all four splits. Feature vectors, scores and threshold decisions matched exactly. Live generation, the OpenCode tool round trip and same-generation parity remain later gates.

The approved cached revision is identified by hash and reproduced the checked features. The historical training revision remains unrecorded. The provenance metadata records conflicting Python versions, and the tracked v2 extractor has merge-conflict markers. The check used the original MVP prompt builder and preserved the existing research artifacts.

Next gate is the shared C0 contract freeze with Developer A. No canonical `contracts/` directory was present in this checkout. B1 and the B4 fixture UI depend on C0.

## C0 — review in progress

The owner confirmed Developer A agrees to proceed with the checkpoint. The [B-side review](../ml/c0-detector-checkpoint.md) records the verified model inputs, wire decisions and Python fixture cases. The A0 evidence and canonical schema were absent from this checkout. Validation against a common schema and both owners' sign-off are pending.
