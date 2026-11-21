# Developer A status

2026-11-21. Baseline `5a10b9a` on `feat/a-opencode-audit`. Implementation lives under `option-a/`. Canonical shared interfaces live under `contracts/`.

| Gate | Status | Evidence or next prerequisite |
| --- | --- | --- |
| A0 | PASS | OpenCode 2.3.2 with Ollama Qwen3 0.6B called the same custom tool in both runs. Allow created the file and produced a matching after event. Deny produced a hook error and no side effect. See the [hook audit](../integrations/opencode-hook-audit.md). |
| C0 A validation | PASS | `node option-a/audit/verify-contracts.mts` accepted or rejected all 10 cases as expected and resolved the API schema references. An A-side Python Draft 2020-12 cross-check also matched all 10 expectations. |
| C0 joint freeze | BLOCKED | A0 and Garv's B0 passed. Garv's independent Python validation and sign-off on the exact shared contract revision are outstanding. Draft is under [contracts](../../contracts/README.md). |
| A1–A5 | BLOCKED | A1 needs A0 and the C0 freeze. After C0, A1–A5 can use a test detector and follow their A-side dependencies. |
| C1 | BLOCKED | Needs C0, A3, A4's real detector client, and B3. |
| C2 | BLOCKED | Needs A5, B5, and C1. Requires real tool calls, same-generation scores, live portal, and sink evidence. |
| A6 | DEFERRED | Optional MCP work follows A2 and A5. |
| A7 | BLOCKED | Needs A5 and C1. Public Option A claims also require C2. |

The project owner approved the architecture and Windows-first scope. Garv is completing B's C0 work. The owner handles pushing once the agreement is complete. Publication remains subject to explicit approval.
