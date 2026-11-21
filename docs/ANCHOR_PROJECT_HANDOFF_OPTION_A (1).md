# Anchor — Complete Project Direction, Hybrid Architecture & Codex Implementation Handoff

> **Current direction (2026-11-21).** The current handoff targets one public distribution and two host adapters. The original package split, primary host and execution order below are superseded. [Dual-host delivery plan](dual-host-plan.md)

## Current handoff

Developer A owns the OpenClaw hook audit, OpenCode regression, shared policy and package entrypoints. Developer B owns the managed Qwen round trip, profile-specific detector qualification and portal. Pair on a real tool call and a verified pre-execution denial before freezing the training profile. Use the linked delivery plan for acceptance evidence.

## Historical OpenCode-first specification

**Revision:** 2026-11-21 (Option A locked)  
**Status:** Authoritative proposed implementation blueprint; not a statement of completed features  
**Primary repository:** https://github.com/haragam22/anchor  
**Comparison reference:** https://github.com/sagarjain03/AegIs  
**Demo agent:** OpenCode  
**Core decision:** **npm/TypeScript-first integration and enforcement; Anchor-managed Qwen2.5-0.5B-Instruct inference with same-path direct activation scoring (Option A); local real-time portal; MCP as an additional adapter.**

> **Read me first — for Codex:** Audit the actual branch, installed OpenCode version, plugin API, dependencies, files, and trained artifacts before implementing. This document supersedes the earlier **MCP-first** / **pip-first** productization recommendation. Preserve existing working research, test artifacts and the Vercel replay application unless an explicitly approved migration is justified. All commands, paths, interfaces, schemas and package names described as *proposed* require implementation and verification. Do not mark any requirement complete from this specification alone.

## 0. Decisions, priorities and non-negotiable principles

### 0.1 Product purpose

Anchor is an **agent-security layer focused on indirect prompt injection through untrusted content, resulting task drift, and attempted unsafe side effects**. The demo must prove a specific security boundary rather than imply universal protection. AegIs is a broader reference for developer experience and presentation, **not** a target for copying every security feature or splitting Anchor into microservices.

### 0.2 Revised decisions

| Topic | Decision |
|---|---|
| Primary distribution | **npm**, TypeScript SDK and OpenCode-native plugin |
| npm package layout | Framework-independent `@anchor-ai/core` plus `@anchor-ai/opencode` adapter; package namespace **provisional, confirm npm availability** |
| Other adapters | `@anchor-ai/mcp` where appropriate; only claim explicitly controlled MCP coverage |
| Python | Required for Option A local Qwen inference, compatible hidden-state extraction and probe scoring during the live ML demo; lightweight npm policy-only installation remains possible for users not enabling ML |
| Primary security authority | One TypeScript policy/taint runtime for live integration, not multiple divergent policy engines |
| Detector | **Selected Option A:** OpenCode uses the same Anchor-managed Qwen2.5-0.5B-Instruct inference service from which Anchor extracts direct activations; deterministic policy-only mode is permitted for integration smoke tests, **not** as a substitute for the final Option A demo |
| Local portal | Live event stream from running enforcement runtime, not replayed JSON |
| Public docs | Separate static documentation site using a docs framework |
| Existing Vercel demo | Keep and label as offline replay unless actually wired to live system |
| Architecture | Monorepo / modular monolith; no mandatory cloud account or hosted backend |
| Enforcement | Before execution for protected side effects; post-output analysis alone is insufficient |
| Demo | Real OpenCode run, controlled fixture/page and fake secret, OFF versus ON, real sink evidence |
| Security claims | Bounded by verified hooks, tool coverage, and model/feature compatibility |

### 0.3 Critical priority order

1. **P0:** Inspect actual integration hooks; demonstrate OpenCode tool-result observation and protected-tool pre-execution gating; build a deterministic controlled OFF/ON test.
2. **P0:** Add run-scoped taint, fail-closed policy, structured events, and proof that no protected sink is invoked on a BLOCK decision.
3. **P0/P1:** Connect a real live event portal to the actual runtime (minimal first).
4. **P1:** Productize npm SDK, OpenCode adapter, CLI, config, reliable installation and integration tests.
5. **P0 for final ML demo:** Integrate the Anchor-owned Qwen inference endpoint with actual OpenCode tool-calling and direct compatible activation extraction; verify feature/probe parity. Do not use shadow scoring as an Option A substitute.
6. **P2:** Documentation website, expanded MCP/other agent adapters, npm publish, optional pip publish, UI polish.

**Rule:** Prove the boundary before polishing; build no dashboard feature that requires invented events.

---

## 1. Previously documented baseline — preserve history and caveats

The earlier handoff describes a historical snapshot, not a fresh full source audit:

- Existing public Vercel demo was `https://anchor-nu-three.vercel.app`; earlier `/api/run` used scenario JSON replay, **not live interception**. Reported API paths: `/api/health`, `/api/scenarios`, `/api/run`, `/api/metrics`.
- A V2 pipeline reportedly included smoke checks, data construction, activation extraction, linear-probe training, external evaluation, action generation and scenario generation, including `v2/offline/extract.py`, `train_probe.py`, `gen_actions.py`.
- Previously reported CPU research model: `Qwen2.5-0.5B-Instruct`; features: hidden state / Δ-state, model-specific probe and threshold.
- Previously reported `docs/STATUS.md` results: **Layer 9, threshold 0.4313; test AUROC 0.998 (127/132), keyword baseline 0.556 (31/132); held-out Hindi 12/22, benign Hindi false blocks 2/22; InjecAgent 20/200, AUROC 0.62 vs keyword 17/200; shuffled-label AUROC 0.494; 2/6 scenario hijacks.** These numbers are setup-specific and should never be used without data, sample-count and external-generalization caveats. Confirm from source before repeating publicly.
- Earlier hardware observations: Intel Core Ultra 7 155H, 16 GB, CPU-only; BF16 path on tested Llama 3B was drastically slower than FP32. Secondary RTX 2050 4 GB smoke-tested a 3B NF4 configuration; smoke-test results are not whole-system benchmarks.
- Earlier `v2/anchor/policy.py` reportedly handled replay/scenario policy, **not** a general-purpose live interception engine.
- Previous MVP phases and status timestamps may now be stale. Audit `README.md`, `docs/flow.md`, `docs/STATUS.md`, `docs/technical.md`, dependencies and all source paths.

**Do not silently overwrite research artifacts, alter probe preprocessing, or conflate replay score, shadow score, and direct model activations.**

---

## 2. Threat model and security boundaries

### 2.1 Threat

An attacker controls a web page, document, repository content or other **untrusted tool output**. The agent is asked to perform a legitimate task, encounters the attacker-supplied content and is persuaded to call a side-effecting tool, for example sending a **fake** secret to a controlled sink. Anchor should detect/restrict consequences according to explicit policy.

### 2.2 Trust boundaries

- **Trusted for controlled demo:** operator configuration, locally administered instrumented tool routes, test harness, event store and fake secret/sink fixtures.
- **Untrusted:** retrieved pages, external documents, arbitrary tool outputs, prompt-injection instructions, and agent-generated side-effect requests.
- **Protected:** only tools/actions which the installed adapter can reliably gate at a **pre-execution** interception point.
- **Not inherently protected:** arbitrary other applications; direct network access outside hooks; uninstrumented raw OS processes; unknown provider/plugin tool paths; model-side activities that never reach an Anchor gate; compromised host/admin.
- **Security property:** the underlying protected side-effect must not execute when policy returns BLOCK, even on scoring timeout, worker crash or malformed response under fail-closed configuration.
- **Trustworthiness:** agent may use another provider/model; npm hooks do not reveal internal activations. Never claim otherwise.

### 2.3 Transparent coverage matrix

Create a runtime `CoverageReport` with `observed`, `pre_execution_gated`, `post_execution_observed`, `ungated`, `unknown`. Display which tool categories/hooks were actually exercised; prohibit claims like “protects every tool” without integration tests. In particular, validate built-in shell/network, filesystem, custom tools, MCP tools, background/subagent execution and any bypass-capable action; mark unsupported routes **UNPROTECTED**, not protected by assumption.

---

## 3. Overall architecture and data flow

```text
                     OpenCode agent runtime
                (messages / tool calls / tool results)
                              |
               verified OpenCode plugin hooks
                              |
                    @anchor-ai/opencode
               lifecycle observation and interception
                              |
                       @anchor-ai/core
          RunContext | Policy | Taint | DetectorClient | Events
                  /            |              \
                 /             |               \
    pre-action ALLOW/BLOCK    score request       event bus
              |                |                    |
    actual wrapped action    Python Qwen service   local API + SSE
             / sink           (owns inference)        |
                                                    live portal

Optional MCP adapter ───────────────> @anchor-ai/core
Documentation website: static external product docs (not runtime path)
Legacy Vercel app: replay/demo, explicitly separate
```

**Ordering contract for untrusted outputs:** tool output observed → classify source → select detector / deterministic exposure policy → update run taint → emit events → agent receives/continues with output as hook permits. Determine actual hook timing; where post-execution observation cannot prevent downstream use, compensate at next *reliably gated* side-effect. Do not claim blocked output was hidden if hook only observes it after forwarding.

**Ordering contract for side effects:** tool invocation proposed → classify action (read-only/side-effect/unknown) → policy evaluation and optional scoring decision → ALLOW then execute, or BLOCK and do not call target → emit outcome. Unknown action classifications default to high-risk in enforce mode where relevant.

**Run identity:** maintain per OpenCode session/conversation and per controlled demo run; avoid process-global taint leakage. Explicit reset and session-lifecycle expiration. Use stable session ID supplied by verified hooks; if unavailable, document fallback and limitations rather than guessing.

---

## 4. OpenCode compatibility: audit before coding

**Current docs indicate a migration between plugin APIs.** Official OpenCode documentation has descriptions of v1 and v2 variants, including v2 `ctx.tool.hook('execute.before'...)`, `ctx.tool.hook('execute.after'...)`, `ctx.session.hook('prompt'...)` and context hooks. The correct package import, hook signatures and error/block semantics depend on the installed version. **Examples in this document are conceptual; do not paste a v1 hook object into a v2 runtime.**

Official references to recheck at implementation time:

- https://opencode.ai/docs/build/plugins/migrate-v1/
- https://opencode.ai/docs/build/plugins/server/
- https://opencode.ai/v2/docs/build/plugins/

### 4.1 Required first audit artifact: `docs/integrations/opencode-hook-audit.md`

Record: exact OpenCode CLI version and commit if possible, plugin SDK version/import path, runtime (Bun/Node), plugin loading mode, documented hook events, tool payload schemas, whether pre-execution hook can synchronously stop/cancel/deny an action, hook ordering, errors propagation, whether post-result hook can modify visible output, stream/response lifecycle coverage, and tested categories of built-in/custom/MCP tools.

| Capability to test | Method | Required evidence |
|---|---|---|
| Plugin actually loads | Minimal local plugin logs one event | Installation/config, version, event with run ID |
| Observe inbound user task | Prompt/session hook where supported | Structured redacted task event |
| Observe built-in tool call | Pre-exec hook with harmless operation | Actual tool name, args schema, invocation ID |
| Observe built-in tool result | Post-exec hook | Real result observed, timing documented |
| Block before protected tool | Gate throws/cancels/denies using supported semantics | Tool side-effect sentinel not created |
| Tool types coverage | Shell/read/write/custom/MCP as allowed | Coverage table, unsupported paths marked |
| Agent response observation | Text/message/session hooks, if available | Observed output and timing; not hidden state |
| Concurrent runs | Two sessions interleaved | No state or secret crossover |
| Timeouts/failures | Deliberate detector/service failure | Protected action blocked and reason logged |

**Gate H0:** If OpenCode's current plugin cannot reliably stop a given sensitive tool, do NOT claim it is protected. Use a controlled wrapped tool/MCP adapter for that particular security proof and label the narrower scope. Decide explicitly whether to ship a version-specific adapter or postpone wider coverage. No inferred coverage.

### 4.2 Plugin behavior

- Minimal overhead on safe routine actions; configurable timeouts; never force Python dependency on SDK installation.
- Decode only necessary data; cap tool output inspection size and record truncation. Avoid raw content exposure in events by default.
- Register as a real plugin by the **verified OpenCode installation format**, both local dev and packaged install.
- Preserve original tool inputs/results unless legitimate configured policy changes require a block/redaction.
- Handle errors with typed reason codes; never swallow exceptions and silently allow a risky action.
- Never call the protected tool outside the gate (including retries, fallback code and demo control paths).

---

## 5. npm packages and responsibilities

Proposed npm scope and names **require registry-availability and trademark checks**. Monorepo may use pnpm workspaces or npm workspaces; pick one and lock versions.

| Package | Responsibility | Coupling |
|---|---|---|
| `@anchor-ai/core` | TypeScript SDK, policy engine, run taint, detector protocol, events, config validation | No OpenCode dependency |
| `@anchor-ai/opencode` | Version-specific native plugin integration and tool lifecycle adapter | Uses `core` |
| `@anchor-ai/cli` | `anchor` executable; config, server, diagnostics, demo/doctor/status/logs | Uses `core`, server |
| `@anchor-ai/server` | Loopback REST API, event streaming, state/API for local portal | Uses `core`, event store |
| `@anchor-ai/mcp` | Optional Anchor-managed MCP tools/proxy (narrow coverage) | Uses `core` |
| `@anchor-ai/demo` (private/internal) | Controlled fixtures, fake secret and sink | Never included in production runtime by default |
| `@anchor-ai/ui` (private build artifact) | Local dashboard frontend | Server serves static build |
| `@anchor-ai/docs` (private) | Static documentation site | No runtime dependency |
| `anchor-ml` / `anchor-ai` (Python naming TBD) | Optional model/probe scoring worker, offline research tools | Separate environment/distribution |

**Avoid circular dependencies.** Core must not import an OpenCode package or UI; Python must not be a required installation for basic policy-only npm use. Keep adapter-specific events normalized into canonical core event types.

### 5.1 Proposed developer installation

```bash
# Proposed published packages — do not claim available before release
npm install @anchor-ai/core
npm install -D @anchor-ai/opencode
npm install -D @anchor-ai/cli

# Local development, from cloned repository
corepack enable
pnpm install --frozen-lockfile
pnpm build
pnpm test
pnpm exec anchor doctor
```

**Production integration is not just `npm install`:** document loading/registering the actual plugin in the verified OpenCode config and prove it is active. Offer `anchor init --agent opencode` to generate a safe config snippet, but do not overwrite users' existing settings without a backup/explicit confirmation. Global installation or `npx`/`pnpm dlx` can be documented only after smoke tests.

### 5.2 Public TypeScript SDK contract (illustrative)

```ts
import { AnchorRuntime, createPolicyDetector } from '@anchor-ai/core';

const anchor = new AnchorRuntime({
  mode: 'enforce',
  detector: createPolicyDetector(),
  failClosed: true,
});
const run = anchor.startRun({ task: 'Summarize this page', sessionId: 'session-1' });
await anchor.observeToolResult({
  runId: run.id,
  toolCallId: 'call-1',
  toolName: 'fetch_untrusted_page',
  trust: 'untrusted',
  content: '...untrusted page text...',
});
const decision = await anchor.authorizeToolCall({
  runId: run.id,
  toolCallId: 'call-2',
  toolName: 'submit_secret',
  actionClass: 'side_effect',
  arguments: { /* redacted in logs */ },
});
if (decision.verdict !== 'allow') throw new Error(decision.reasonCode);
// Execute tool ONLY after ALLOW.
```

Define actual TypeScript public APIs via tested code and examples. Expose asynchronous operations because detector may be remote/subprocess. Include cancellation, timeout and queue limits; return typed decisions instead of ambiguous booleans.

### 5.3 Required API types

- `AnchorRuntime`: `startRun`, `observeToolResult`, `authorizeToolCall`, `endRun`, `getRunStatus`, `subscribeEvents`, `resetDemoRun` (reset restricted to operator).
- `RunContext`: `runId`, `sessionId`, task fingerprint (not raw secret by default), mode, taint state, detector mode/version, config fingerprint, sequence number, created/updated timestamps.
- `Detector`: `score(observation, context) -> DetectorResult` with `score | null`, `threshold | null`, `model`, `probeVersion`, `detectorMode`, `errorCode`, `latencyMs`, `evidenceSummary` (redacted).
- `Policy`: `authorize(ActionContext) -> PolicyDecision` with verdict `allow | block | require_approval`, reason code, rules triggered, taint snapshot, trace ID.
- `ToolObservation`: source trust, content (internal only), content hash, byte count, truncation metadata, tool call ID and timestamps.
- `SecurityEvent`: versioned immutable envelope, redaction and ordering.

**Invariant:** `require_approval` is a denial by default until a working operator approval system exists; do not silently execute it. Safety verdicts should not be overwritten by failures in the UI/event store.

---

## 6. Taint and policy engine (single live authority)

### 6.1 Modes and meanings

- `off`: observe and log, but intentionally permit controlled demo actions. **Unsafe and only allowed in an explicitly isolated demonstration environment.** Must not be confused with a recommended production configuration.
- `monitor`: inspect, record what would block, but do not enforce. Clearly identify hypothetical decisions.
- `enforce`: inspect and block protected side effects under relevant policy and taint conditions; fail-closed on critical scoring failures.

Use explicit policy capability selection: `detector_mode: policy_only | direct_managed_qwen`. `policy_only` is for smoke tests or installations without ML; **Option A live demonstration requires `direct_managed_qwen`**. Shadow scoring is outside the selected scope. A deterministic exposure rule such as “untrusted tool output received” can taint without ML; label the cause `policy_exposure`, not ML detection.

### 6.2 Suggested taint states

`clean` → `untrusted_observed` → `tainted` (or `scoring_error`) → `closed`. Decide via policy whether benign inspected content remains `untrusted_observed` versus `clean`; record both exposure and risk. Taint should be monotonic within the protected run except through an audited operator reset/start of a new run. Do not clear taint because later messages appear benign.

### 6.3 Policy decisions

Rules, in precedence order: explicit demo isolation and operator controls; hard-block protected destinations/actions; fail-closed if scorer unavailable (for protected side effects); taint-related block; permitted read-only/allowlisted actions; unknown high-risk actions default block where configured. Encode precedence and test it. UI cannot change runtime policy without an authorized local config/control endpoint.

### 6.4 Race/error safety

- Observe async tool results and score before updating/clearing the gate for later actions; maintain a per-run atomic sequence or serialized reducer.
- Verify concurrency: two actions arriving simultaneously cannot bypass taint due to delayed scoring.
- Detector timeout: explicit `detector_timeout` and fail closed for protected actions; cache only if cache key includes necessary model/config/version and content context.
- Worker crash: no fail-open fallback in enforce mode for protected actions.
- Invalid config: fail startup instead of quietly disabling protection.
- Replayable audit events use monotonically increasing run sequence numbers; redaction happens before persistence/transmission.

---

## 7. Python activation-detector subsystem

### 7.1 Why Python remains

Existing research uses PyTorch/Transformers/Qwen activations and a trained linear probe. Rewriting this in TypeScript would add risk without granting any greater access to OpenCode's internal model states. Preserve its verified preprocessing/inference/evaluation pipeline.

### 7.2 Final detector decision — **Option A (mandatory target)**

**The user selected Option A.** OpenCode must send its real generation requests to an **Anchor-managed inference endpoint serving the exact compatible `Qwen2.5-0.5B-Instruct` model**. Anchor must extract the required hidden states **inside that same inference execution path**, compare a correctly constructed task/tool-context Δ-state, apply the existing validated linear probe and send a traceable score to the TypeScript policy engine. This is **direct activation scoring of the actual configured OpenCode agent model**, not separate reconstructed shadow scoring.

Deterministic source-taint and policy-only mode remains useful for earlier tool-hook/connectivity gates and for non-ML users of the npm core. It is **not** the accepted end state for the Option A demonstration. **No automatic shadow-Qwen fallback.** If the exact model, compatible activations or proper context mapping are unavailable, return `unavailable`/`incompatible` and fail closed for protected side effects; mark the Option A gate **BLOCKED**, do not silently relabel a shadow score as direct.

### 7.3 Mandatory inference and OpenCode compatibility experiment

1. **Inventory probe provenance:** Find trained probe artifact and metadata, exact model revision, model file hashes, tokenizer files/revision, chat template, layer (historically layer 9), token index/position, Δ-state extraction algorithm, normalization and input format, threshold (historically 0.4313), dtype/precision and dependencies. Historical numbers are references to verify, not configuration defaults guaranteed to work.
2. **Implement local managed inference:** A Python/Transformers-based service should load the verified model once, reuse its tokenizer/template, expose an OpenAI-compatible endpoint **only to the extent OpenCode really requires**, and access hidden states from the same forward passes that generate model outputs. Do not invent a fake model API that just wraps an unrelated provider. Ensure streaming, message roles and tool-call support where required; record exact model ID and feature provenance per request.
3. **Configure OpenCode to use it:** Prefer its supported custom OpenAI-compatible provider path (`providers`, provider package and `settings.baseURL`), verified against current docs and installed version. A sample configuration must use real verified model IDs, context limits and **actual** tool-calling capabilities, not inferred capability declarations. Documentation: https://opencode.ai/docs/providers and https://opencode.ai/docs/models .
4. **Prove agent viability separately:** Qwen2.5-0.5B-Instruct is a small model; **successful OpenCode tool use is not guaranteed**. Test model request, multi-turn conversation, tool schema parsing, actual tool choice/arguments, streaming if needed, tool result injection, and repeated tool calls. If tool-call format is unsupported, implement/validate an adapter only if it preserves semantics; otherwise report Option A blocked, do not quietly switch the demo model.
5. **Direct-state experiment:** At the relevant tool-output boundary, correlate the exact OpenCode session, model generation request, tokenized before/after contexts and hidden-state extraction. A hook receiving tool output cannot by itself expose model activations. Explicitly document whether score evaluates incoming untrusted content by an **additional controlled forward pass of the same model** or on **actual generation forward-pass activations**; only the latter is strictly direct agent-generation activation scoring. If using an additional pass, call it *same-model auxiliary scoring*, never claim it is the original forward pass.
6. **Parity test:** Reproduce trusted offline probe scores with identical fixture contexts; compare CPU and selected accelerators if tested, establish measured score tolerances and latency, and verify detection timing relative to downstream side-effect gating. Pin the verified build. Reject precision, quantization or template changes that break parity until a new probe is trained and independently evaluated.
7. **Prove actual control:** OpenCode must use **this** managed model for the complete OFF and ON controlled demo; inspect gateway request logs, per-run request IDs, expected tool calls, intercepted output, scored activation records and pre-action BLOCK. If OpenCode falls back to an external provider or another model, abort the demo as invalid.

**Design note:** A single inference service can both serve model tokens and compute hidden-state features; the Node/TypeScript package remains the enforcement and integration authority. Do not create a separate second Qwen run under the name "direct scoring" or make the Python service the competing policy authority.

### 7.4 Service API and request correlation (proposed contracts)

| Endpoint | Function |
|---|---|
| `GET /health` | Process availability, model readiness, loaded probe and tool-call readiness |
| `GET /metadata` | Exact model/probe hashes, tokenizer/template, dtype, extraction config and declared capabilities |
| `POST /v1/chat/completions` | OpenAI-compatible chat + tool-call handling, **validated by OpenCode compatibility tests** |
| `GET /v1/models` | Expose verified model identifier and supported capabilities, if required |
| `POST /v1/score` | Optional explicit same-model scoring for diagnostic comparison; **not** proof of original generation hidden states |
| `GET /v1/activations/{request_id}` or an internal event channel | Correlated activation/probe result from the actual managed inference path; secure and bounded |

Example activation result schema (illustrative):

```json
{
  "schemaVersion": "1",
  "detectorMode": "direct_managed_qwen",
  "inferenceRequestId": "req-example",
  "runId": "demo-example",
  "modelId": "Qwen2.5-0.5B-Instruct-pinned-revision",
  "probeHash": "verified-artifact-sha256",
  "featureExtractionHash": "verified-pipeline-sha256",
  "layer": 9,
  "threshold": 0.4313,
  "score": null,
  "status": "pending_verification",
  "latencyMs": null
}
```

**Never fabricate an activation score.** `null` indicates that this sample describes a wire format rather than a measured result. All measured events must carry actual request correlation, provenance and error/status fields. Authenticate/bind to loopback, enforce size limits, handle worker crashes and redact secrets before persistence.

### 7.5 Gating policy and run modes

- `mode=off`: The **same** managed model endpoint, tools and monitoring path execute; enforcement disabled, detector can still log. The sink must receive the demo secret only if the real agent attempts the action.
- `mode=enforce`: The same model and tool route; a verified activation/probe risk or explicitly configured deterministic taint policy gates a protected side effect **before** execution. Event history identifies which signal actually caused each block.
- `detector_required=true` for Option A showcase: if model/probe is missing, incompatible, late or crashes, protected side effects fail closed; the demo is not considered complete.
- Invariant: model generation is not inherently equivalent to a blocking signal. Use the OpenCode plugin's actual pre-execution hook for policy, and prove the hook fires before the sink.

### 7.6 Mandatory final demonstrations and proof artifacts

- Working custom provider and actual OpenCode agent run through Anchor-managed Qwen, with tool calls confirmed.
- Captured evidence that token generation and the captured hidden states belong to the same underlying model execution; no provider fallback.
- Replayable `request_id` → `session_id` → `tool_result_id` → `activation_score_event` → `taint_transition` → `policy_decision` → `sink_outcome` linkage.
- OFF controlled sink receives fake secret; ON blocked sink receives no secret; both use equivalent fixtures and model, with exact outcomes captured.
- Benign control task, scoring failure, timeouts, incompatible feature extractor, tool-call failure and concurrent runs all tested.
- Benchmark actual Qwen CPU/GPU response and scoring latency on available hardware. Explicitly document when performance makes Option A impractical for a smooth live demo.

---

## 7A. Option A rollout dependencies (do not skip)

A **minimum policy-only smoke test** may precede model integration because it isolates whether OpenCode hooks can block a tool. However **the final live-detection success criterion requires Option A**, so the managed Qwen/provider/probe compatibility work must be completed **before** the final claimed detector-backed ON/OFF demo and before publishing ML functionality. If the exact runtime cannot interoperate with OpenCode or cannot yield compatible activations, report a blocked gate with experimental evidence and alternatives to the owner for a *new decision*; do not downgrade the selected architecture without approval.

---

## 8. CLI contract — `anchor`

CLI can ship from `@anchor-ai/cli` as a Node executable; its exact binary name must be checked for conflicts.

| Command | Behavior | Validation |
|---|---|---|
| `anchor init --agent opencode` | Generate annotated `anchor.yaml` and version-correct OpenCode integration snippet | Never overwrite without confirmation; no secrets embedded |
| `anchor doctor` | Check Node/Bun, OpenCode version/plugin compatibility, config, detector connectivity, bound ports, UI build | Actionable errors and exit codes |
| `anchor serve` | Start loopback API + portal + event store | `/health` and live event endpoint work |
| `anchor plugin verify` | Check plugin load and hooks/coverage from actual sentinel events | Reports UNKNOWN where tests absent |
| `anchor demo --mode off|enforce` | Start/reset isolated demo with controlled fixtures | Deterministic fixture, user-visible mode warning |
| `anchor status` | Mode, run IDs, detector info, observed coverage, server health | No secrets displayed |
| `anchor logs [--run ID] [--json]` | Read redacted persisted events | Filter, correct ordering, pagination |
| `anchor config validate` | Validate schema and security-sensitive fields | Nonzero exit on unsafe errors |
| `anchor ml doctor` | Managed Qwen inference environment, probe metadata and OpenCode provider compatibility | Helpful setup guidance if missing |
| `anchor version` | npm package, event/config schema and adapter versions | Does not hide incompatibility |

All commands have `--help`, predictable exit codes, Windows/macOS/Linux path handling where tested, and a global `--config`. Never auto-download large models or start unrequested network services merely for help/status.

---

## 9. Configuration contract

One top-level `anchor.yaml`; parse/validate with a versioned schema (e.g. Zod in Node) and reject unknown critical/security keys. This is a **proposed configuration, not proof of implemented compatibility**:

```yaml
schema_version: 1
anchor:
  mode: enforce              # off | monitor | enforce
  fail_closed: true
  bind_local_only: true

integration:
  opencode:
    enabled: true
    version_policy: strict
    require_pre_tool_gate: true
  mcp:
    enabled: false

runtime:
  taint_on_untrusted_exposure: true
  score_timeout_ms: 5000
  max_inspection_bytes: 250000
  run_state_ttl_minutes: 60

policy:
  unknown_side_effect: block
  block_side_effect_when_tainted: true
  allow_read_only_when_tainted: true
  protected_tools:
    - submit_secret

```

Additional detector/server fields (merge with the preceding YAML into a single valid config):

```yaml
detector:
  mode: direct_managed_qwen # required for Option A live demo
  required: true
  endpoint: http://127.0.0.1:8766
  threshold: null          # resolve from verified probe metadata, not a universal default

server:
  host: 127.0.0.1
  port: 8080
  events: sse
  persist_redacted_events: true

demo:
  enabled: false
  controlled_sink_only: true
```

> **Implementation instruction:** The blocks above are a *field proposal*; combine into **one syntactically valid starter YAML** in the repository. Do not retain the explanatory invalid placeholder. Choose defaults based on actual runtime behavior; `off` must not be default. Define config precedence (CLI > env > file only where explicitly documented), validation, migration and safe reload/restart behavior.

---

## 10. Local live portal requirements

**URL (proposed):** `http://127.0.0.1:8080` — loopback-only, not public. This is **not** the documentation website and **not** the legacy Vercel replay UI.

### 10.1 Screens and fields

| Screen | Minimum live content |
|---|---|
| Overview | Active runs, enforcement mode, plugin connected, detector mode/health, protected/ungated tool counts |
| Live Timeline | Real timestamped calls/results, taint transitions, decisions, sink outcomes, latency |
| Agent Session | Session ID, task summary, tool-call lineage, visible response summaries where supported |
| Risk/Detector | Score **if real**, threshold, score provenance, model/probe version, timeout/failure reason |
| Taint & Policy | Per-run taint state, action class, rule reason, allow/block, fail-closed evidence |
| Coverage | Hook names and tools verified gated; explicit unsupported/unknown pathways |
| Demo | Reset, isolate OFF/ON runs, controlled fixture selection, sink result verification |
| Audit History | Previous run timelines, filtering, compare runs, exported redacted JSON/CSV |
| Settings/Diagnostics | Read-only config view, API/plugin health, schema/compatibility warnings |

### 10.2 Example real event timeline (illustrative only)

```text
10:32:01  RUN_STARTED           session=demo-on
10:32:03  TOOL_CALL             fetch_untrusted_page
10:32:04  TOOL_OUTPUT_OBSERVED  source=untrusted
10:32:04  DETECTOR_RESULT       mode=direct_managed_qwen score=<measured value>
10:32:04  TAINT_UPDATED         score/policy cause → tainted
10:32:06  TOOL_PRE_EXECUTION    submit_secret
10:32:06  POLICY_DECISION       BLOCK reason=TAINTED_SIDE_EFFECT
10:32:06  SINK_VERIFICATION     deliveries=0
```

**Event provenance must be traceable** to a concrete plugin hook, tool adapter or detector call. No static JSON may be passed off as live activity. OFF and ON should show different sink outcomes with matching fixture/task/tool route, not different pipelines.

### 10.3 Local API/event transport

- `GET /health`, `GET /v1/status`, `GET /v1/runs`, `GET /v1/runs/:id/events`, `GET /v1/coverage`, `GET /v1/config/safe`.
- `GET /v1/events/stream` — Server-Sent Events recommended for one-way real-time log feed; reconnect with event ID/cursor and replay from persisted storage. WebSocket only if bidirectional controls demand it.
- `POST /v1/demo/reset`, `POST /v1/demo/start`, `POST /v1/demo/stop` — local operator-only controls, never public unauthenticated endpoints. Separate UI from enforcement; dashboard outage must not bypass policy.
- Store redacted events in bounded local JSONL/SQLite (choose one via implementation spike), support retention and size limits; do not log secret value except intentionally isolated test sink proof.
- CORS restrictive, `127.0.0.1` default, origin checks and CSRF protections for state-changing local endpoints; consider local auth/token in multiuser environments. Validate JSON, avoid exposing executable arbitrary paths or remote URLs.
- Detect stream gaps/order mismatches and surface them instead of silently claiming a complete audit.

### 10.4 UX acceptance

Show explicit statuses for `policy-only smoke test`, `direct managed Qwen`, and `unavailable`; no invented score. Mobile/tablet responsive is optional; desktop presentation must be readable. Demonstration operators can reset without manually editing DB. Include safe empty states when OpenCode disconnected and a prominent coverage warning when a side effect is not gated.

---

## 11. Controlled demo contract

### 11.1 Objective

Have OpenCode receive a malicious page while doing a benign task (e.g. “Read this page and summarize it”), with access to a **fake** demo secret (`ANCHOR_DEMO_SECRET_7391`) via explicit test context or `get_demo_secret`. The page induces an attempt to send this fake value via controlled `submit_secret`. With enforcement OFF the controlled sink receives it; with ON, the same protected tool call is blocked before execution.

### 11.2 Fixture/tools

- `fetch_untrusted_page`: returns locally controlled benign or malicious page and records source trust classification.
- `get_demo_secret`: optional safe source of fake secret, with redacted audit event.
- `submit_secret`: isolated in-memory/loopback sink (no real external exfiltration); invocation routed through verified pre-exec gate.
- `get_demo_status`: read-only proof of attempts/deliveries and hashes.
- `reset_demo`: operator-only; resets taint, sink and run records for both modes.

### 11.3 Comparison rules

1. Both runs use same agent/model/config/task/page and same tool route. Only enforcement mode differs; reset run state and sink between runs.
2. Confirm secret is **actually available to the agent**; otherwise the test proves nothing about exfiltration prevention.
3. Verify OFF run agent **attempts** `submit_secret` and sink receives exact fake secret; if attack does not induce a call, mark inconclusive, do not fake success.
4. Verify ON run sees same malicious page and blocked `submit_secret` attempt; sink delivery count remains zero.
5. Distinguish detected *attack* from observed *untrusted exposure*. Policy-only can prove boundary enforcement without validating ML drift detection.
6. Record time, versions, detector mode, tool path and event trail; test non-injection page separately.
7. The prompt and malicious content must be limited to **isolated fake-secret controlled demo fixtures**; never use actual keys, personal information or public third-party sinks.

### 11.4 Escape route / plugin-coverage risk

A real agent may use an unprotected shell/curl/network tool instead of `submit_secret`. Preempt this in the controlled demo by disabling non-Anchor egress/tool routes **where supported** and recording remaining coverage. This does **not** prove universal protection; a stronger claim requires real built-in tool gating and bypass tests.

---

## 12. Optional MCP adapter

MCP remains valuable for broad agent interoperability and for deterministic controlled tools. It is **secondary**, not the main developer entry point for OpenCode.

- Route incoming tools into the **same core policy engine** as the OpenCode plugin. Avoid reimplementing taint in Python MCP or duplicating policy rules.
- MCP can gate actions **only for tools flowing through its own controlled server/proxy**, not arbitrary built-in shell tools or other MCP servers.
- Provide minimal `fetch_untrusted_page`, `submit_secret` and status fixtures for regression tests.
- Include stable run/session identification, auth for protected state and tool call timeouts.
- Publish clear install instructions for compatible MCP clients without claiming they expose agent hidden states.
- An MCP-only demo is an explicit fallback if plugin pre-exec blocking proves unusable for a selected tool category.

---

## 13. Public documentation website

Choose MkDocs Material or VitePress; since the primary SDK is TS, **VitePress** is a reasonable default, but don't create a custom docs framework. Site is static and independent of live operations.

Proposed navigation:

1. **Introduction:** what Anchor does, scope, threat model, what is not covered.
2. **Getting started:** system requirements, npm install, `anchor init`, OpenCode plugin activation, first protected tool, OFF/ON controlled demo.
3. **Architecture:** plugin hooks, core runtime, detector modes, policy path, portal, MCP differences.
4. **TypeScript SDK:** public API, examples, typed errors, async lifecycle, adapters.
5. **OpenCode:** version compatibility matrix, configuration examples, hooks/coverage, debugging, bypass cautions.
6. **MCP / other agents:** adapter installation, limitations, adding custom tool wrappers.
7. **Python ML / Option A:** required managed inference for final ML demo, compatible OpenCode provider setup, trained probe artifacts, same-pass activations, precision/feature compatibility and evaluation caveats.
8. **Configuration:** annotated complete YAML, schema, modes, fail-closed, environment variables, default ports.
9. **CLI:** commands with verified stdout/exit codes and troubleshooting.
10. **Local portal / API:** endpoints, SSE examples, event schema, audit redaction, security posture.
11. **Security & evaluations:** threat model, controlled benchmark methodology, full dataset counts, false positives, limitations, responsible disclosure.
12. **Development, release & contributing:** monorepo, CI, release, semantic versioning, support matrix.

Build docs from checked-in examples and executable snippets as much as practical. Publish only after local install instructions work in a fresh environment. Keep Vercel replay explicitly separate from portal screenshots.

---

## 14. Repository structure — target, not a command to delete existing files

```text
anchor/                                # existing repository, preserve history
  README.md
  ANCHOR_PROJECT_HANDOFF_NPM_HYBRID.md
  package.json                          # private workspace root
  pnpm-workspace.yaml                   # if pnpm selected
  pnpm-lock.yaml
  tsconfig.base.json
  anchor.example.yaml
  packages/
    core/src/
      runtime/RunContext.ts
      runtime/AnchorRuntime.ts
      policy/PolicyEngine.ts
      taint/TaintStore.ts
      detector/Detector.ts
      detector/PolicyDetector.ts
      detector/PythonDetectorClient.ts
      events/schema.ts
      events/bus.ts
      config/schema.ts
      index.ts
    opencode/src/
      index.ts                            # verified version-specific plugin
      hook-adapter.ts
      coverage.ts
    cli/src/
      index.ts
      commands/{init,doctor,serve,demo,status,logs,config}.ts
    server/src/
      api.ts
      sse.ts
      events-store.ts
    mcp/src/
      index.ts
  apps/
    portal/src/                          # React/Vite or similarly simple UI
    docs/                                # VitePress/MkDocs static site
  demo/
    fixtures/{benign_page,malicious_page}.md
    sink/
    scripts/
  python/
    scorer/                              # wrapper around existing artifacts
    tests/
  tests/
    unit/
    integration/
    e2e/
    fixtures/
  docs/
    integrations/opencode-hook-audit.md
    architecture.md
    threat-model.md
    evaluation.md
    implementation-status.md
  v2/                                     # retain existing research and demo
  .github/workflows/
```

**Migration rules:** Do not automatically move the existing `v2/` Python tree; avoid duplicate `anchor` import confusion; first add TS workspace alongside existing files. Extract code only after tests and dependency graph prove it safe. Keep one authoritative *live* policy implementation. Historical replay policy can remain under explicit replay namespace.

---

## 15. Data contracts and event schema

### 15.1 Canonical security event (example)

```json
{
  "schemaVersion": 1,
  "eventId": "evt-000013",
  "runId": "run-001",
  "sessionId": "session-001",
  "sequence": 13,
  "timestamp": "2026-11-21T00:00:00.000Z",
  "source": "opencode_plugin",
  "kind": "policy_decision",
  "toolCallId": "tool-004",
  "toolName": "submit_secret",
  "actionClass": "side_effect",
  "detectorMode": "policy_only",
  "score": null,
  "threshold": null,
  "taintState": "tainted",
  "verdict": "block",
  "reasonCode": "TAINTED_SIDE_EFFECT",
  "latencyMs": 2,
  "redacted": true
}
```

### 15.2 Stability requirements

- Schema changes versioned independently and accompanied by fixture/test migration.
- Use run/session/tool-call correlation keys; clock is UTC ISO 8601; canonical sequence is monotonic within run.
- Emit `tool_output_observed`, `detector_result`, `taint_updated`, `tool_pre_execution`, `policy_decision`, `tool_finished`, `sink_verification`, `error`, `run_started`, `run_closed`, `coverage_report`.
- Score is `null` when no ML detector ran; never populate a simulated value in production event streams.
- Sanitize secrets, URLs with credential query parameters, raw request body, PII, and full retrieved page by default; include content hash and snippets if needed and safe.
- The event stream and UI are not enforcement authorities; event persistence errors must not turn a BLOCK into an ALLOW.

---

## 16. Test strategy and quality gates

### 16.1 Unit tests

- State machine transitions, one-run taint isolation, no implicit untainting, sequence ordering.
- Policy precedence, unknown tool classification, allowlisted read-only action, blocked side effects.
- Fail-closed on timeout, malformed detector reply, HTTP 500, refused connection, invalid JSON.
- Config schema defaults/unknown security fields/environment overrides.
- Event serialization/redaction, content truncation and hash determinism.
- Idempotent duplicate calls; cancellation, retries and double-execution prevention.

### 16.2 Integration tests

- Plugin actually loads in pinned OpenCode version; pre-exec and post-exec events contain usable IDs.
- Real tool execution blocked before any sentinel side effect; show proof independent from UI.
- Two concurrent agent sessions with different taint states remain isolated.
- One tool output arrives while another protected action is attempted: no race-based bypass.
- Python scorer response, metadata compatibility, error/timeouts; policy-only runs without Python installed.
- SSE reconnection, event ordering, auth/origin checks and bounded storage.
- MCP adapter behavior uses the same policy and event schema.

### 16.3 End-to-end acceptance

- Fresh clone + install + build + start + OpenCode integration + local portal, using documented commands.
- Controlled OFF run leaks *fake* secret only to controlled sink; ON run blocks it; real events prove difference.
- Benign page remains allowed under chosen policy; unexpected blocks reported and analyzed.
- Plugin coverage report exposes ungated routes and exact version limits.
- Every displayed detector score maps to a real scorer invocation with provenance.
- `npm pack` tarballs contain built JS/types/README/license and **exclude** secrets, model weights, test fixtures unless intentionally packaged.
- No internet needed for local *policy-only* demo after dependencies installed (model/scorer modes document further requirements).

---

## 17. Detailed Codex implementation roadmap (phases 0–11)

Each phase must produce a commit-sized deliverable, tests, a `docs/implementation-status.md` update, and a **pass/fail validation gate**. Do not mark phase complete based solely on code being written. Cross-phase work may overlap only when prerequisites remain satisfied.

### Phase 0 — Source and compatibility audit (G0)

**Prereqs:** Clone repo, access installed OpenCode. **Tasks:** inspect tree, git status, existing Python probe assets, current web replay, dependency lockfiles; compare old handoff claims with source; verify official OpenCode version docs and SDK; produce hook/coverage matrix, runtime plan, list of reusable code, blockers and implementation decisions. **Artifacts:** `docs/implementation-status.md`, `docs/integrations/opencode-hook-audit.md`, `docs/architecture.md`. **Gate G0:** written inventory of actual versus proposed, plugin version pinned, proof plan for pre-tool deny semantics, no edits that erase existing work.

### Phase 1 — TypeScript workspace scaffold (G1)

**Prereqs:** G0. **Tasks:** establish workspaces and lockfile; TS build, lint, formatter, Vitest or equivalent, package exports/types, shared versioning and module boundaries. Add tiny `@anchor-ai/core`, `@anchor-ai/opencode` local adapter with diagnostics. **Gate G1:** clean install/build/test from a fresh checkout; no Python needed.

### Phase 2 — OpenCode plugin hook spike (G2)

**Prereqs:** G1 and version-specific hook audit. **Tasks:** load actual plugin, capture session/tool name/result, test hook timing, pre-execution deny using sentinel side effect, test tool types and event failures, document concrete config and migration differences. **Gate G2:** independently verified actual tool cannot execute when denied; unsupported tools explicitly declared. **Fallback:** retain narrower wrapped tool/MCP boundary and label product coverage accordingly.

### Phase 3 — Run state, core policy and event engine (G3)

**Prereqs:** G2. **Tasks:** implement typed run state, trust classification, taint transitions, policy reasons, fail-closed behavior, action classification, audit event bus, in-memory persistence/test harness. **Gate G3:** unit tests for concurrency, timeouts, unknown actions and policy invariants; blocked action never calls target.

### Phase 4 — Controlled OpenCode OFF/ON **policy-only smoke test** (G4)

**Prereqs:** G3. **Tasks:** fixtures, fake secret injection, harmless sink, reset, real OpenCode test, reproducible script. Use policy-only first. **Gate G4:** OFF sink receives secret and ON sink receives none with same tool path/task; event evidence and agent attempt verified; no outside egress. If attack does not cause attempt, report inconclusive and iterate fixture rather than claiming success.

### Phase 5 — Live local API and minimal portal (G5)

**Prereqs:** G3–G4. **Tasks:** loopback server, structured event store, SSE, frontend run timeline, current mode and coverage, real sink result, basic diagnostics. **Gate G5:** dashboard updates as *actual* tool events occur, correlates with sink evidence; service shutdown doesn't bypass core policy.

### Phase 6 — npm SDK and OpenCode distribution (G6)

**Prereqs:** G2–G5. **Tasks:** stable TypeScript API, package exports/typings, package metadata, example plugin config, compatibility matrix, npm pack and local tarball installation, optional workspace test consumer. **Gate G6:** outside the monorepo a clean sample project can install package tarball, load plugin and enforce a controlled side effect. No unnecessary ML dependencies.

### Phase 7 — CLI and YAML config (G7)

**Prereqs:** G6. **Tasks:** `init`, `doctor`, `plugin verify`, `serve`, `demo`, `status`, `logs`, schema validation, cross-platform paths. **Gate G7:** end-to-end setup from CLI works; unsafe/unknown config fails with actionable errors; starter config is valid YAML.

### Phase 8 — Option A managed Qwen inference + direct activation scoring (G8)

**Prereqs:** G0 provenance inventory; G2 verified OpenCode hooks; G3 policy runtime; G4 controlled test. **Tasks:** pin exact Qwen model/tokenizer/probe; build an Anchor-managed Python inference server with OpenCode-compatible chat and actual tool-call behavior; configure OpenCode custom provider; capture same-inference hidden states; re-create task/tool Δ-state correctly; run parity/regression experiments; correlate inference/tool/score IDs; implement Node client, timeouts and fail-closed; measure real latency and memory. **Gate G8:** OpenCode actually calls the managed Qwen model, successfully uses tools, activation records demonstrably originate from the same inference, model/probe feature compatibility verified, and a detector-backed ON/OFF run exhibits the expected sink results. If any of these fail, **G8 BLOCKED**; do not switch to shadow inference or claim that the earlier G4 policy-only demo proves Option A.

### Phase 9 — MCP portability and expanded coverage (G9)

**Prereqs:** G3 and G6; after demo if schedule tight. **Tasks:** optional MCP adapter wired to core, verified client setup, additional pre-tool coverage tests and honest gaps. **Gate G9:** MCP tools obey same decision/event contracts; no global interception claims.

### Phase 10 — Complete portal + public docs (G10)

**Prereqs:** G5–G8. **Tasks:** risk/provenance details, filters, audit history, comparison screen, redaction/coverage views; static docs with SDK/CLI/config/OpenCode/MCP/ML/reference and honest evaluation. **Gate G10:** docs build, links pass, instructions succeed on clean machine; dashboard has zero fabricated data; exposed settings secure.

### Phase 11 — Release hardening and publication (G11)

**Prereqs:** G6–G10. **Tasks:** CI matrix, dependency/security audits, lockfile reproducibility, source maps/licensing, SemVer policy, npm 2FA/provenance, `npm pack` smoke, PyPI release optional, tagged release, rollback/publish checklist and demo video. **Gate G11:** publish only from clean CI, no tokens or weights shipped accidentally, installed artifact works outside repo, test report attached. Do not publish packages without explicit project-owner approval.

### 17.1 Scope gates

- **Policy-only prototype:** G0–G5 complete, plus enough G6/G7 for reproducible developer setup; explicitly **not** Option A complete.
- **Option A live-demo-ready / Developer-alpha:** G0–G8 complete, including successful OpenCode Qwen tool-calling, verified same-inference activation scoring, detector-backed OFF/ON test, API/compatibility documentation and regression tests.
- **Public release:** G0–G11 as applicable and documented; coverage/limitations visible.
- Skip optional polish, never skip the mandatory gate in pursuit of a release date.

---

## 18. CI/CD, security and release workflow

- CI on pull requests: formatting/typecheck/unit tests, npm workspace build, integration tests with pinned plugin/API when feasible, Python research/scorer tests if relevant, docs link/build, package pack inspection.
- CI on release: clean packed npm install in empty directory, binary smoke test, sample OpenCode plugin registration, portal starts, demo harness proves enforce mode, artifact licenses/manifest, SBOM/security advisory review.
- Automated dependency updates must not silently upgrade the OpenCode plugin API beyond compatibility matrix.
- No real credentials in fixtures, committed `.env`, logs, screenshots, docs, demo sinks or published npm package. Token scanning and redaction tests.
- Use `npm pack --dry-run` (or package manager equivalent); verify exports CJS/ESM only as needed; support declared Node versions (set after audit). Test Windows and Linux, ideally macOS in CI.
- Keep registry names provisional until availability confirmed. Publish npm and optionally PyPI as *separate* releases with compatible documented protocol versions.
- Document deterministic upgrade/rollback, version compatibility, local server privacy defaults and isolation.

---

## 19. Product positioning and AegIs comparison

Anchor differentiator: **focused and evidence-backed control of indirect prompt injection → run taint → pre-side-effect blocking**, with activation-detector research available where justified. AegIs may inspire clear product pages, screenshots, onboarding and developer docs; avoid copying breadth, marketing claims, or unnecessarily multiplying services. Keep the UI truthful about actual threat coverage.

**Potential homepage tagline (proposal):** “Anchor — Detect untrusted agent context. Enforce before side effects.” Add a factual qualifier explaining exact supported adapters and modes.

---

## 20. Explicit prohibitions / avoidable mistakes

- Do **not** present the older replay Vercel demo as live.
- Do **not** assert that installing npm automatically instruments all agents or tools.
- Do **not** infer that response messages expose hidden-state activations.
- Do **not** call a Qwen shadow score the actual OpenCode model's activation score.
- Do **not** apply Qwen-trained probe to another model or change precision/template without revalidation.
- Do **not** let a UI/logging outage bypass enforcement.
- Do **not** create multiple contradictory TS/Python policy authorities.
- Do **not** ship OFF mode as secure default or allow it on exposed endpoints by accident.
- Do **not** mark a blocked *attempt* as confirmed if agent never called the protected tool.
- Do **not** use actual credentials or uncontrolled exfiltration targets.
- Do **not** claim policy-only enforcement proves ML detection.
- Do **not** add broad security product features, extra models/datasets or microservices before core demo works.
- Do **not** publish npm/PyPI or deploy publicly merely because a local build succeeds.
- Do **not** silently rewrite existing repository history, status results or established artifacts.

---

## 21. Final acceptance checklist

### Hook boundary and threat proof
- [ ] Pinned OpenCode version, correct plugin API, actual plugin loaded.
- [ ] Supported pre-execution tool gate prevents sentinel side effect.
- [ ] Tool post-output observation and agent-visible content timing documented.
- [ ] Coverage matrix explicitly distinguishes protected, observed-only and unprotected tools.
- [ ] Real controlled malicious page, fake secret and sink; two independent clean runs.
- [ ] OFF agent attempts sending fake secret and sink receives it.
- [ ] ON agent attempts sending fake secret and sink is never invoked.
- [ ] Benign scenario, scorer errors/timeouts, concurrent sessions, bypass attempts tested.

### Product and ML
- [ ] Clean npm tarball install works; TypeScript SDK and plugin have usable examples/types.
- [ ] Policy-only installation requires no Python/torch/model download.
- [ ] `anchor init`, `doctor`, `plugin verify`, `serve`, `demo`, `status`, `logs` work.
- [ ] Validated and versioned config; unsafe modes clearly labeled.
- [ ] Python scorer optional and mode metadata accurate; trained artifact compatibility tested.
- [ ] No fabricated direct-activation or cross-model claims.

### UI, docs and release
- [ ] Live portal receives real event stream, accurately reports score/taint/decision/sink.
- [ ] Coverage, detector provenance, redaction and audit history are clear.
- [ ] Offline replay website clearly separated from live portal.
- [ ] Public docs install/config/API/limitations current and build successfully.
- [ ] CI and fresh-install tests pass; package inspected for secrets/unneeded assets.
- [ ] Owner explicitly approves publication/deployment.

---

## 22. Codex operating instructions and immediate first prompt

**Working agreement:** On every phase, state the current architecture, files changed, tests run, results, unverified assumptions, remaining blockers and next gate. Make minimal reversible changes; ask for missing *secrets/credentials* only if genuinely necessary (the demo should not require them). Avoid starting research/model training just to satisfy a product packaging task.

**Paste into Codex to begin:**

> Treat `ANCHOR_PROJECT_HANDOFF_OPTION_A.md` as the current authoritative target specification. The owner has **selected Option A**: managed Qwen inference, actual compatible model hidden states and direct activation detection, not shadow scoring. Do not implement everything at once. First complete Phase 0 only: inspect the current Git branch, repository source, existing replay/demo and Qwen probe artifacts, installed OpenCode version and official plugin API. Determine whether tool execution can be blocked *before* the real side effect in this version; verify which hooks observe tool results/agent response and which built-in/MCP tools are gated. Produce `docs/implementation-status.md`, `docs/integrations/opencode-hook-audit.md` and a minimal architecture decision record. List concrete blockers and proposed next changes. Do not delete existing files, silently migrate research pipelines, claim universal coverage, publish packages or start building the portal. Stop at Gate G0 with tested evidence and a concise report.

---

## 23. Source references and confidence

- **User-supplied original handoff:** `ANCHOR_PROJECT_HANDOFF.md` (631-line historical scope, demo/security baseline).
- **User-supplied prior revised handoff:** `ANCHOR_PROJECT_HANDOFF_REVISED.md` (prior pip/MCP-first productization ideas; superseded for distribution priorities).
- **Public project repo:** https://github.com/haragam22/anchor (must audit live code branch, not assume status snapshot).
- **Comparison reference:** https://github.com/sagarjain03/AegIs (presentation/positioning inspiration only).
- **OpenCode official plugin migration guide:** https://opencode.ai/docs/build/plugins/migrate-v1/
- **OpenCode official plugin API documentation:** https://opencode.ai/docs/build/plugins/server/ and https://opencode.ai/v2/docs/build/plugins/

**Verification level:** This is a specification incorporating provided handoffs and public plugin documentation, **not** a certified full repository audit or tested OpenCode integration. Any claims about exact plugin hook semantics must be confirmed against the selected installed version at G0/G2. Historical reported detector metrics and hardware measurements require reconfirmation from original records before publication.


## 24. Decision record — Option A locked (2026-11-21)

**Selected by project owner:** Model integration Option A from the original handoff, i.e. OpenCode uses the Anchor-managed exact compatible Qwen2.5-0.5B model with activation access. The other proposed options (shadow-Qwen and policy-only) are **not** acceptable substitutes for the claimed detector-backed final demo. They may be used strictly as explicitly labeled diagnostic or integration milestones. Acceptance G8 is mandatory. Changes require a new recorded owner decision.
