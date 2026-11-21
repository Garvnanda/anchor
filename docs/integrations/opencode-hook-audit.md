# OpenCode hook and coverage audit

Audit target: Windows x64, Node 24.11.0, npm 11.6.1, OpenCode CLI and `@opencode/plugin` 2.3.2. The plugin reported Bun 1.4.4. The workstation has OpenCode Desktop 1.18.29.0 and Ollama 0.33.3. The audit uses an isolated CLI installation to pin the V2 API. The machine has about 15.7 GiB of physical memory and Intel Arc integrated graphics.

## Repository baseline

- The baseline has no npm workspace, package lock, or native OpenCode adapter. The two November handoff documents control the new effort.
- `mvp/` is the frozen replay app. `v2/api/index.py` also reads JSON scenarios and runs the replay policy. `v2/api/live.py` adds an explicit scoring request to a separate API, and `v2/agent/loop.py` contains a separate JSON action loop with Pipelock. Those routes provide prior research and experiments. The new TypeScript runtime governs live OpenCode actions.
- Qwen artifacts are present in `v2/offline/out/qwen0.5b/`, including `probe.json` and `probe_meta.json`. B0 owns compatibility and provenance verification. Prior score and model decisions in `docs/decisions.md` are historical. The baseline has historical conflict markers in `docs/decisions.md` and `docs/STATUS.md`.

## Hook API and evidence

The SDK's V2 default export uses a plugin ID and `setup(ctx)`. The native audit uses local `.opencode/plugins/audit.ts` discovery. The SDK declarations expose:

- `session.hook("prompt")` with `sessionID`, `messageID`, and prompt parts.
- `tool.hook("execute.before")` with `tool`, `sessionID`, `messageID`, `agent`, `id`, and mutable `input`. The official migration example throws from this hook to deny a request.
- `tool.hook("execute.after")` with the same identities and a completed result or error. The documented API permits replacing a successful result. The sentinel checks order and observed result, and result replacement remains unverified.
- `session.hook("http.request")` and `session.hook("http.response")` with session ID, request kind, model reference and HTTP objects. A primary request header reached the local Ollama route in the transport check below. Response correlation, message streaming and other provider paths need separate tests.

See the [server plugin reference](https://opencode.ai/docs/build/plugins/server/) and [V1 migration guide](https://opencode.ai/docs/build/plugins/migrate-v1/). Hook types alone do not establish runtime coverage.

| Route | Coverage | Evidence needed |
| --- | --- | --- |
| Custom `audit_sentinel` | observed, pre_execution_gated, post_execution_observed | Same local tool attempted in both sessions. Allow created the sentinel and returned its marker. Deny raised the hook error before the executor and left no file. |
| Built-in read/write/edit | unknown | Exercise each candidate invocation path independently. |
| Built-in shell/network | unknown | Run harmless local checks before making coverage claims. |
| MCP, Code Mode, background and subagent tools | unknown | Each path needs an independent test. The custom fixture uses direct tool calling. |
| Other applications and tool paths outside the adapter | ungated | Outside the OpenCode hook boundary. |

## A0 result

PASS for the custom tool route on OpenCode 2.3.2. The real local Ollama `qwen3:0.6b` made a tool call in each case. An earlier Qwen3.5 9B run timed out and an earlier 0.6B run produced invalid arguments. The final comparison used the same zero-argument tool and prompt in both sessions.

| Case | OpenCode call ID | Hook and filesystem evidence |
| --- | --- | --- |
| Allow | `call_xtb5p0n1` | Prompt and before events share a session. The executor wrote the file with exclusive creation. A matching completed after event included the marker, and the harness read back the exact file bytes. |
| Deny | `call_qq3qqxs2` | Prompt and before events share a different session. The before hook recorded denial, OpenCode surfaced `ANCHOR_AUDIT_DENIED`, and the independent file check found no sentinel. There was no executor or after event for the denied call. |

The audit command exited zero and printed `A0 sentinel verified`. Local trace: `option-a/.cache/sentinel-bsxDbq/`. The tested call is a harmless capability check. The managed Qwen activation path, protection of additional tools, concurrent sessions, scorer failure, and the A3 and C2 demos have separate gates. See [audit commands](../../option-a/README.md).

## Provider transport follow-up for C0

OpenCode 2.3.2 made two real `POST /v1/chat/completions` requests to Ollama Qwen3 0.6B through a loopback proxy. The first request had no tool history. After the sentinel ran, the second request contained these matching identifiers:

| Location | ID |
| --- | --- |
| Plugin `execute.before` and `execute.after` event `id` | `call_bkhj961c` |
| Assistant message `tool_calls[0].id` | `call_bkhj961c` |
| Tool message `tool_call_id` | `call_bkhj961c` |

The `session.http.request` callback copied the request with a test header containing `event.sessionID`. Both primary requests arrived with the same session ID as the tool hooks. Only IDs and route names were captured in the probe output. The check used one completed custom tool call and did not exercise retries, parallel calls, or auxiliary requests.

The installed `@opencode/ai` OpenAI-compatible chat adapter delegates to the OpenAI chat serializer. That serializer uses the part's `id` for both fields unless the route provides a tool ID conversion function. B1 and C1 should verify the join by exact ID on the managed provider, including any rewrite, and treat missing or ambiguous matches as unavailable.
