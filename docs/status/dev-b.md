# Developer B status

## B0 — PASS


The packaged managed Qwen controls generated real layer-9 scores and reached policy decisions in the portal. Both hosts reached managed inference. The native host policy remains exposure-based pending host-profile detector qualification. [Judge guide](../../option-a/distribution/README.md)

The Option A target is managed Qwen generation serving OpenCode, with detector evidence captured from that generation path. The [probe audit](../ml/probe-provenance.md) and [inference audit](../ml/inference-feasibility.md) record the implemented historical path and the remaining evidence gaps.

Validated the local model snapshot and artifact hashes, compared probe parameters and cached feature hashes, counted dataset splits, and inspected local runtimes and tracked source. With owner approval, tested the cached snapshot offline in CPU FP32 against 12 historical MVP rows spanning all four splits. Feature vectors, scores and threshold decisions matched exactly. Live generation, the OpenCode tool round trip and same-generation parity remain later gates.

The approved cached revision is identified by hash and reproduced the checked features. The historical training revision remains unrecorded. The provenance metadata records conflicting Python versions, and the tracked v2 extractor has merge-conflict markers. The check used the original MVP prompt builder and preserved the existing research artifacts.

Next gate is the shared C0 contract freeze with Developer A. B1 and the B4 fixture UI depend on C0.

## C0 — PASS

Reviewed A0 and the shared contract at `c4adfab7f6f23d1273384caa5b00fc0d76d3b863`. Developer A recorded a TypeScript validation pass on the proposal. Developer B independently ran `python -B tests/python/test_c0_contract.py -v`. It checked all three schema definitions and all 10 shared cases (five security-event and five detector-result) with a Draft 2020-12 validator and format checking. B accepts the tested schema shapes for this revision.

The owner confirmed agreement from both sides to freeze this revision and verify the mapping between provider-native tool call IDs and OpenCode hook IDs during B1. Required detection reports unavailable whenever the match is missing or ambiguous. The [shared proposal](../../contracts/README.md) remains the wire reference.

## B1 — PASS for the controlled tool-call spike

Ran `node option-a/python/b1_smoke.mjs` with OpenCode 2.3.2 and the pinned CPU FP32 snapshot. Qwen generated both tool calls with valid arguments. OpenCode executed both tools, returned both results with the original call IDs and received the correct final answer from the local endpoint. Both provider call IDs matched the OpenCode hook IDs in the observed run. See the [B1 evidence and reproducer](../ml/b1-tool-call-spike.md).

Full Anchor header delivery and retries remain integration checks.

## B2 — BLOCKED on live feature compatibility

Ran the approved single-result comparison followed by the two-result experiment. Captured layer-9 prefill features from the actual Qwen generation calls and matched their tool IDs to OpenCode. The saved MVP fixture reproduced exactly, but the live single-result vector differed from the historical-format reference by up to 0.599557 per feature. Two results in one continuation produced one aggregate diagnostic measurement. See the [B2 parity report](../ml/parity-report.md) for commands, scores, timings and scope.

The owner approved prompt isolation and broader evaluation. `node option-a/python/b1_smoke.mjs --parity-single --isolate-prompt` passed all harness checks. Both reconstructed endpoints matched exactly, and the system messages and tool definitions produced the largest individual feature shifts on this example.

`node option-a/python/b1_smoke.mjs --parity-single --evaluate` completed the original 205-row MVP test split. With the unchanged model, probe and threshold, OpenCode-format examples yielded 37/132 detections and 8/73 benign false positives. The historical features yielded 127/132 and 1/73 respectively. Feature parity failed for all 205 OpenCode-format rows. B3 remains gated on a validated live feature path. See the [results and reproducer](../ml/parity-report.md).

## Later phases and team handoff

| Phase | Gate | Evidence and outstanding dependency |
| --- | --- | --- |
| B2 | BLOCKED | At the historical false-positive budget of one benign flag, the best possible single cutoff on the observed test scores caught 22/132 positives. Changing the threshold alone cannot restore the historical 127/132 result. The frozen probe and historical threshold are preserved for team review. |
| B3 | BLOCKED | The authenticated loopback service exposes health, metadata, real model serving and activation lookup. Health reports incompatible. Known correlated pairs return incompatible and missing pairs return 404. Eight cold-start HTTP checks passed. A compatible same-generation detector result remains required for C1. |
| B4 | PASS for the fixture dashboard | From an isolated npm install, the browser test rendered all eleven event kinds, checked mobile width, keyboard disclosure, streamed reconnect and duplicate suppression. Three unit tests passed. The production build excludes development fixtures. See [portal verification](../dashboard/local-portal.md). |
| B5 | BLOCKED on A4/A5 | The static dashboard, bearer-authenticated REST/SSE consumer and [local developer guide](../../option-a/apps/docs/index.html) are available. Real API events, sink receipts and external SDK/CLI installation need Person A's server and packages. |
| B6 | BLOCKED on B2/B3/C1 | The [evaluation report](../ml/evaluation-report.md) records offline scores, operating-point feasibility, CPU timings, memory and evidence limitations. Integrated detector and enforcement timing remains unmeasured. |
| B7 | Windows startup verified; full gate BLOCKED | Created a new Windows Python 3.12.14 environment with 35 pinned packages, verified the cached snapshot, started the service and tested its HTTP failure behavior. The reference host already had the weights cached. Full acceptance requires B3/B6 and fresh-machine verification on each claimed platform. |

> **Current direction (2026-11-21).** Next, capture the OpenClaw managed-provider round trip and measure the post-tool prompt before training. [Dual-host delivery plan](../dual-host-plan.md)
## Deep verification and remaining acceptance gates

- **B3 transport verified.** A real Qwen generation carrying two tool results produced two independently schema-validated incompatible records with null scores. Tested incomplete, duplicate and mismatched identities, unknown lookup, malformed streaming options, service loss, a stalled client, a competing generation, and health during the stall. Known incompatible pairs return HTTP 200 with their status; unknown pairs return 404. B2 still prevents a ready direct result. The [integration guide](../ml/detector-integration.md) records exact client behavior and test commands.
- **B4 passed.** The browser exercised unauthorized access, all eleven event kinds, keyboard and accessibility checks, duplicate suppression, resume by event ID, expired-cursor HTTP 409, snapshot recovery, and visible incomplete-history status.
- **B5 frontend and guides built.** The dashboard consumer and documentation are ready for Person A's server. Both local and remote main were checked at c4adfab. The A4 event server and A5 SDK/CLI are absent, so live sink, SSE and external-install acceptance remain pending.
- **B6 evaluation evidence verified.** Independently recomputed the true-positive counts, benign flags and pairwise AUROCs for both formats from all 249 saved row measurements. Provider failure behavior was tested directly. Combined detector/enforcement latency and proof of fail-closed side effects require C1.
- **B7 Windows clean-environment check passed.** Copied only the Python source, dependency lock, launcher and probe to a clean directory, installed 35 pinned packages into a new Python 3.12.14 environment, loaded the verified model from the host cache and passed all eight startup HTTP checks. This satisfies the clean-environment startup test on the reference Windows host. No other OS was tested. Full project acceptance still depends on the B3/B6 gates.

## Person B checkpoint verification

C0 remains passed at contract revision c4adfab. All ten shared fixtures were revalidated. C1 provider checks passed with a real generation, two correlated incompatible results, process loss, restart, stale-record rejection and OpenAPI validation. The C2 benign OpenCode control passed against the authenticated managed endpoint with two completed tool hooks and the correct final answer. The B2 diagnostic activation trace was independently matched to its original hook and generation IDs. Dashboard fixture and reconnect checks passed again.

The joint C1 and C2 gates remain open for B2 compatibility and A-owned runtime, policy, sink and release evidence. See the [checkpoint handoff](../ml/c1-c2-person-b.md) for commands, evidence boundaries and remaining acceptance items.
