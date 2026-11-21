# C0 contract proposal

Status: **proposed v1**. The project owner approved the architecture on 2026-11-21. A0 and B0 passed. Developer A's fixture validation passed. Freeze after Garv's independent validation and both owners' sign-off on the same revision.

The new implementation root is `option-a/`. A owns the npm workspaces, TypeScript runtime, native adapter, and loopback API. B owns managed Qwen, probe validation, dashboard, and public docs. Shared wire contracts live here. The TypeScript core is the sole runtime authorization authority.

Reference toolchain for review: OpenCode CLI and plugin SDK 2.3.2, Node 24 and npm 11 on Windows x64. B0 validated the cached Qwen snapshot using Python 3.12.14 and CPU FP32. The Python serving dependency lock is B7 scope. B1 needs to run the real provider round trip with the selected OpenCode release.

| Contract | Maintainer | Consumer |
| --- | --- | --- |
| Security event and coverage | A | B dashboard |
| Detector result and metadata | B producer, A client, both review schema | A runtime, B dashboard via redacted events |
| Portal REST/SSE | A | B dashboard |
| OpenAI-compatible serving route | B | OpenCode via the A adapter |

## Correlation and authorization

- OpenCode `sessionID` maps to `sessionId`. Anchor issues `runId` for a run within the session. OpenCode tool hook `id` maps to `toolCallId` within that session. A protected action has its own call ID, distinct from the observed result that contributed evidence.
- The proposed provider transport attaches fresh `X-Anchor-Inference-Request-Id`, `X-Anchor-Run-Id` and `X-Anchor-Session-Id` headers to each primary HTTP generation request to the configured local managed provider. B binds each ID to that exact request and rejects duplicates or mismatches. Correlate only after verifying that the request actually contains the tool result. One request can evaluate multiple tool outputs, so result lookup additionally takes the source `toolCallId`. For C0 review, A and B need to agree how provider-native tool call IDs map to OpenCode tool hook IDs. If the mapping is missing or ambiguous, required detection is unavailable. No time-based joins.
- V2 SDK `session.http.request` exposes the request and session on paper. A1/C1 must verify header delivery, result identity, retries, and exclusion of title and compaction calls in the pinned runtime. The exact `POST /v1/chat/completions` dialect, including streaming and roles, will be captured by B1 against real OpenCode traffic.
- A validates all returned identity fields, provenance hashes, model revision, precision, layer, threshold, and timing independently of JSON Schema. A ready auxiliary result is diagnostic only. Required direct mode denies protected actions if same-generation evidence is missing, late, incompatible, or cannot be correlated. Neither scores nor transport statuses contain authorization decisions.
- In a detector event, envelope and payload IDs must agree. Runtime checks enforce cross-field and cross-record invariants: matching IDs, monotonic run sequence, immutable event IDs, receipt count/hash consistency, and a real observed attempt before claiming a denied sink outcome.

## Portal and sink

Use `/api/*` for the portal and the separate detector's `/health`, `/metadata`, and `/v1/activations/{inferenceRequestId}?toolCallId=...`. A missing activation pair returns `404`. A applies a bounded lookup deadline before releasing a protected action. Request budgets and the probe metadata pin are measured and agreed at C1. Bind both services to loopback, use separate local bearer credentials, validate Host and Origin, and keep tokens out of URLs. Portal SSE uses fetch streaming to send the bearer header. Administrative routes are outside this proposal.

The SSE `id` is the opaque event ID. Replay retained events after `Last-Event-ID` in server append order, preserving per-run sequence. An expired cursor returns `409` before streaming so the client can fetch a fresh snapshot and display the gap. Only real runtime records enter the live feed. Fixture payloads are for contract tests.

The demo sink is a dedicated controlled tool with a separate local receipt log. A's verified tool boundary gates it before execution. Use only synthetic data and report count plus a hash, with raw payload excluded from events.

## Validation and freeze

Run `node option-a/audit/verify-contracts.mts` from the repository root after installing the audit tooling. On B's side, configure a Draft 2020-12 validator to register all three schemas by their `$id`, enable format checking, and evaluate each case in `fixtures/cases.json` against its named schema. Fixture scores are synthetic schema examples. Each side records the command and result against the same commit.

During joint review, resolve the provider-to-hook tool ID mapping and record B0, both validation results, and both approvals in the A/B status logs. The schemas are closed to reject unreviewed payload fields. Deploy optional v1 additions only after both validators and fixtures accept them. A breaking change requires joint review, fixture migration and a version bump.
