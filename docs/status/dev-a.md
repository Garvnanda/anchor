# Developer A status

> **Current direction (2026-11-21).** Next, prove OpenClaw pre-execution denial with a counted local sink and retain the pinned OpenCode regression. [Dual-host delivery plan](../dual-host-plan.md)


The packed adapters now run on both pinned hosts. OpenClaw blocked a real local write. OpenCode observed real managed tool calls. The shared monitor can follow either JSONL stream. [Judge guide](../../option-a/distribution/README.md)

2026-11-21. A0 and the C0 proposal are on `main`. Implementation lives under `option-a/`. Shared interfaces live under `contracts/`.

| Gate | Status | Evidence or next prerequisite |
| --- | --- | --- |
| A0 | PASS | OpenCode 2.3.2 with Ollama Qwen3 0.6B called the same custom tool in both runs. Allow created the file and produced a matching after event. Deny produced a hook error and no side effect. See the [hook audit](../integrations/opencode-hook-audit.md). |
| C0 A validation | PASS | `node option-a/audit/verify-contracts.mts` accepted or rejected all 10 cases as expected and resolved the API schema references. An A-side Python Draft 2020-12 cross-check also matched all 10 expectations. |
| C0 joint freeze | BLOCKED | A0 and Garv's B0 passed. Garv's independent Python validation and sign-off on the exact shared contract revision are outstanding. Draft is under [contracts](../../contracts/README.md). |
| A1 | IMPLEMENTED AGAINST PROPOSED C0 | The owner authorized starting before the freeze. The locked workspace builds, the observation test validates event shape and isolation, and OpenCode 2.3.2 loads the compiled plugin and emits events correlated to the real sentinel attempt. |
| A2 | UNIT TESTS PASS | The TypeScript gate blocks missing state, a pending untrusted output, taint, invalid evidence, timeout, and a score race. The new runtime's real OpenCode sink comparison remains open. |
| A3 | INCONCLUSIVE | OpenCode read the local fixture in both OFF trials but did not call the sink. There is no OFF receipt or ON comparison to count yet. |
| A4 | LOOPBACK TESTS PASS | The authenticated API streams actual TypeScript runtime events. Resume, expired cursor, access rejection, detector HTTP failures and policy remaining active after portal shutdown are covered. The packaged OpenCode portal example and Garv's live dashboard still need a joint run. |
| A5 | PENDING | External package/CLI verification follows A2 and A4. |
| C1 | AWAITS JOINT RUN | Use Garv's latest local build to confirm C0 and verify the managed service, request identities, latency and failure handling. A compatible same-generation result is required for the successful-score control. |
| C2 | BLOCKED | Needs A5, B5, and C1. Requires real tool calls, same-generation scores, live portal, and sink evidence. |
| A6 | DEFERRED | Optional MCP work follows A2 and A5. |
| A7 | BLOCKED | Needs A5 and C1. Public Option A claims also require C2. |

The project owner approved the architecture and Windows-first scope and directed A to defer inspection of Garv's local code and validation until the joint C1 integration. The owner handles pushing. Publication remains subject to explicit approval.

A1 verification on Windows used `npm ci`, `npm test`, and `npm run test:opencode` from `option-a/`. The live trace contains a prompt, before hook, output observation, and completion event for a real local tool call. A separate sentinel trace confirmed the matching session and call IDs. The observation log contained fingerprints and metadata. See the [workspace instructions](../../option-a/README.md).
