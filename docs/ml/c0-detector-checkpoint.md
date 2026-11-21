# C0 detector checkpoint — Developer B review

This is Developer B's input for the shared contract freeze. The canonical schema and wire examples will come from the shared contract review. Developer A owns the TypeScript stub and schema changes. Developer B owns the Python fixture and validation against the same schema.

## Evidence available for the contract

- B0 passed on the approved cached `Qwen/Qwen2.5-0.5B-Instruct` revision `7ae557604adf67be50417f59c2c2f167def9a775`. CPU FP32 reproduced all 12 sampled MVP feature vectors, scores and threshold decisions exactly. See [probe provenance](probe-provenance.md).
- Installed OpenCode reports `1.18.27`. A0 must supply the selected version and observed provider and hook behavior. B1 must capture the actual chat request, tool-call response and follow-up request with tool output.
- The handoff proposes `POST /v1/chat/completions` for model inference, `GET /health` and `GET /metadata` for diagnostics, and either `GET /v1/activations/{request_id}` or an internal event channel for the detector result. The portal API is a separate interface owned by A.

## Decisions for the shared review

| Topic | Decision to record |
| --- | --- |
| Provider and runtime | Selected OpenCode version from A0, custom-provider settings, Node and Python versions, loopback binding and auth expectations. |
| Request identity | Who generates `runId`, `sessionId`, `toolCallId` and `inferenceRequestId`, where they travel, and how a follow-up generation maps to one or several preceding tool calls. Specify duplicate, mismatch and cross-run lookup behavior. Timestamp proximity is insufficient evidence for a join. |
| Result transport and timing | Activation lookup endpoint or internal event channel. Define pending, missing and expired results, when the detector deadline begins, and the budget A's client enforces. |
| Result shape | Finalize field names, required and nullable fields, status and error codes, digest formats, precision, layer, score and threshold bounds, and the value and evidence required for `generation_forward_pass`. |
| Portal contract | Canonical REST/SSE paths, resume cursor and ordering, event schemas, auth and coverage vocabulary. The plan illustrates `/api/...` routes and the handoff illustrates `/v1/...` routes. Record the agreed prefix before building the fixture UI. |

## Python fixture cases for the frozen schema

| Case | Expected contract behavior |
| --- | --- |
| Correlated generation result | A complete result carries the actual run and inference identities, compatible provenance, and a numeric score and threshold. A measured fixture must be clearly identified as a fixture. |
| Unavailable, incompatible, error or timeout | Each status is representable with a null score. The agreed error fields distinguish causes for the client. |
| Malformed payload | Missing required identity or provenance, wrong field types, unknown statuses and out-of-range scores are rejected where applicable under the schema. |
| Cross-request evidence | Two individually valid results can still have different run or inference identities. The fixture should exercise the agreed correlation check as well as JSON validation. |
| Artifact mismatch | Include a structurally valid result with an unexpected model revision or probe hash so the compatibility check can reject it independently of JSON validation. |

C0 acceptance requires the Python fixture and TypeScript stub to validate independently against the same canonical schema, with sign-off from both owners. B1 starts once that gate passes.
