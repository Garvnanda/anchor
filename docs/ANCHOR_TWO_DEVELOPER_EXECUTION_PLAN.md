# Anchor — Two-Developer Parallel Execution Plan

> **Current direction (2026-11-21).** Use the linked plan for current assignments, dependencies and acceptance gates. The phases below document the earlier OpenCode-first work. [Dual-host delivery plan](dual-host-plan.md)

## Current handoff

Developer A owns the OpenClaw hook audit, OpenCode regression, shared policy and package entrypoints. Developer B owns the managed Qwen round trip, profile-specific detector qualification and portal. Pair on a real tool call and a verified pre-execution denial before freezing the training profile. Use the linked delivery plan for acceptance evidence.

## Historical OpenCode-first specification

**Revision:** 2026-11-21  
**Companion specification:** `ANCHOR_PROJECT_HANDOFF_OPTION_A.md`  
**Status:** Proposed allocation; no phase is assumed complete.  
**Architecture locked:** TypeScript/npm-first OpenCode integration and enforcement; Python-managed Qwen2.5-0.5B-Instruct serving OpenCode with verified same-generation activation scoring (Option A); live local portal; optional MCP adapter.  
**Priority:** Minimize shared-file editing, maximize independent phase progress, synchronize only at explicit integration gates.

> **Operating rule:** This document allocates responsibility; the Option A handoff controls technical/security requirements. If they conflict, document the conflict and reconcile it at the next contract checkpoint. Codex must audit actual files and capabilities first. Never mark a phase PASS from code existence alone.

## 1. Assignment and boundary of ownership

| Area | Developer A — Agent & Enforcement | Developer B — ML & Product Experience |
|---|---|---|
| Main language | TypeScript / Node | Python + frontend TypeScript |
| Owns | OpenCode native adapter, `@anchor-ai/core`, taint/policy, CLI, npm build/release, optional MCP | Managed Qwen inference, activation/probe fidelity, evaluation, detector service, local portal UI, documentation site |
| Integration interfaces | Owns TypeScript `DetectorClient` and tool/session events | Owns Python service and detector response implementation; UI consumes versioned events |
| Source of truth | Policy decisions and run-state reside in A's core | Actual model activations/probe results reside in B's managed inference service |
| Must NOT do | Train/change probe, implement substitute shadow detector, build competing Python policy | Duplicate TypeScript policy engine, bypass plugin gates, introduce UI-only security state |
| Shared scope | 3 formal checkpoints; one nominated integration driver per checkpoint | Same |

**Allocation note:** Assign A/B to actual names later; do not create a hard dependency on either person's identity. A owns the live local API/event store because it is tightly coupled to enforcement. B owns the **dashboard frontend** and public documentation. The interface between them is a versioned event schema plus a loopback API/SSE contract. This intentionally avoids both editing the same runtime files.

### 1.1 File/directory ownership (proposed; reconcile with actual repo in audit)

**A-exclusive:** `packages/core/**`, `packages/opencode/**`, `packages/cli/**`, `packages/server/**`, `packages/mcp/**`, `packages/demo/**`, `tests/ts/**`, `docs/integrations/opencode-*.md`, `docs/policy/**`.

**B-exclusive:** `python/**` or existing `v2/offline/**` plus new serving modules, `apps/dashboard/**`, `apps/docs/**`, `tests/python/**`, `docs/ml/**`, `docs/dashboard/**`. Existing research data/probe artifacts must not be changed without explicit provenance review.

**Controlled/shared files:** root `package.json`, root `pnpm-lock.yaml`, workspace config, CI workflows, root README, `docs/architecture.md`, `contracts/**`, `docs/implementation-status.md`. **A owns merges/edits to shared workspace/CI files** after B supplies requested dependency/build details. **Contract files only change through a shared contract PR.** Each developer logs progress in their own file: `docs/status/dev-a.md` and `docs/status/dev-b.md`.

**Source-control practices:** `feat/a-*` and `feat/b-*` branches; small PRs; no force pushes to shared main; rebase on contract-tagged baseline; merge only after applicable gate PASS. Prefer generated contract types from canonical schema over duplicate handwritten types.

## 2. Three explicit collaboration checkpoints

### C0 — Contract freeze (short joint checkpoint, before primary implementation)
**Prerequisites:** A0 and B0 audits.  
**Decisions:** Monorepo paths; chosen OpenCode version and hook/blocking semantics; Node/Python runtimes; package names provisional; canonical `runId`, `sessionId`, `toolCallId`, `inferenceRequestId`; REST/SSE URLs; event/version schema; detector status/error/timeout schema; demo sink boundary; managed model/provider ownership; capability/coverage vocabulary.  
**Outputs:** `contracts/README.md`, `contracts/security-event.schema.json`, `contracts/detector-result.schema.json`, `contracts/api.openapi.yaml` (or equivalent), sample valid/invalid fixtures, protocol examples, assigned interface maintainers.  
**Gate C0:** A's TS stub and B's Python fixture independently validate against *the same schema*; contract tests pass; no unspecified required field; both sign off. Freeze `v1` for parallel work; changes via explicit contract PR.

### C1 — Integration handshake (after A3 + B3, can happen before polished UI)
**Prerequisites:** A's real policy gate + detector client; B's managed Qwen service + provenance/activation proof; C0.  
**Procedure:** Start real Python service; A calls `health`, `metadata` and correlated scoring/result endpoint; provoke malformed JSON, timeout, crash, mismatched probe/model hash; verify protected action fail-closed; compare detector and policy records by IDs.  
**Gate C1:** Schemas, latency budget, correlation and error codes verified in both processes. **Not** equivalent to final end-to-end Option A success. A owns runtime integration; B owns Python diagnosis.

### C2 — Full demo and release acceptance (after mandatory A/B phases)
**Prerequisites:** A5 and B5, and C1.  
**Procedure:** OpenCode configured to the same Anchor-owned Qwen endpoint for OFF/ON; genuine tool use; controlled fake-secret page and sink; real generation activation provenance; dashboard live timeline; independent sink evidence; benign and failure controls.  
**Gate C2:** OFF controlled sink receives fake secret **only if agent actually attempted it**; ON blocks before sink execution with measured score and direct same-generation evidence; no unsupported protection claims. Test fresh installation and rollback. If Qwen cannot perform required tool call, gate is **BLOCKED**, not passed via policy-only or shadow scoring.

## 3. Dependency model — maximize parallelism

```text
A0 repo + OpenCode audit ──┐
                         ├── C0 schema freeze ── A1 plugin spike ── A2 core/policy ── A3 controlled demo
B0 probe + Qwen audit ───┘                  └── B1 model/tool-call spike ── B2 provenance/scorer ── B3 API
                                                                                A3 + B3 ── C1
A4 server/events ── A5 npm/CLI ── A6 MCP (optional) ── A7 hardening ──────────────┐
B4 UI from fixtures ── B5 real UI + docs ── B6 evaluation/performance ──────────────┤── C2
                                                                               A/B integration
```

**Parallel independence strategies:** A tests against a contract-valid `FakeDetectorClient`, including failures. B tests Python with HTTP harness and fixture calls, independent of OpenCode, then separately tests OpenCode-provider viability. B builds dashboard against **contract sample events** until A's live SSE is available; samples must be visibly marked as development fixtures and cannot be shown as live security results. A builds server using a minimal static diagnostic page until B's UI is ready.

**Critical path warning:** B's managed Qwen OpenCode tool-calling and same-generation activation work is highest technical risk. Begin B1 immediately after C0, not after npm packaging. A should likewise validate pre-execution denial in A1 before investing heavily in the TypeScript runtime.

## 4. Developer A — seven independent phases

### A0 — Repository and OpenCode hook audit
**Prerequisites:** Access to actual repository, ability to install/check OpenCode.  
**Tasks:** Audit existing structure, modules, current CLI and SDK, relevant hooks, version, pre/post execution order, safe cancellation of side effects, coverage of built-ins/custom/MCP/subagents; test harmless sentinel. Locate preservation constraints for existing replay demo.  
**Deliverables:** `docs/integrations/opencode-hook-audit.md`, A-owned audit/coverage table, A's `docs/status/dev-a.md`.  
**Gate A0:** Pinned OpenCode version, runnable observed tool-call proof, demonstrated or explicitly unverified deny semantics for each proposed protected tool, list of unsupported paths. No assumption that post-execution observation can block past side effects.  
**On failure:** Mark unsupported paths UNPROTECTED; identify narrow controlled wrapped-tool alternative, do not claim universal interception.

### A1 — Workspace, SDK skeleton, native plugin load
**Prerequisites:** A0 + C0 (contract v1).  
**Tasks:** Scaffold `@anchor-ai/core`, `@anchor-ai/opencode` with one package manager/lockfile, build/typing/test; wire real plugin load/session observation/tool-result observation, typed normalized events. Keep SDK installable without Python.  
**Deliverables:** Workspace packages, plugin registration sample, TS fixtures/tests.  
**Gate A1:** Clean install/build/test; plugin loaded in installed OpenCode version; real task and tool outputs visible with correlation IDs; no unexplained unsupported imports.  
**On failure:** Stop downstream A2 gating claims until plugin load/version fixed.

### A2 — Policy, run-state and pre-execution enforcement
**Prerequisites:** A1, contract schemas, a demonstrated supported pre-execution blocking hook for protected action.  
**Tasks:** `RunContext`, source classification, monotonic taint, `off|monitor|enforce`, `policy_only|direct_managed_qwen`, fail-closed detector-client interface, verdict reason codes, concurrency/timeout/error tests; no direct sink access outside gate. FakeDetectorClient for local tests.  
**Deliverables:** Core runtime, deterministic tests, classification/coverage matrix.  
**Gate A2:** 100% of specified protected sink cases prove **no underlying call on BLOCK**; concurrent sessions isolated, delayed score cannot race with protected action, scorer errors/timeouts block protected side effects in enforce mode; normal read-only controls succeed.  
**On failure:** No dashboard/release can be described as protective.

### A3 — Controlled real OpenCode demo, policy-only smoke
**Prerequisites:** A2.  
**Tasks:** Controlled benign/malicious page, fake secret, local `submit_secret` sink, reset, OFF/ON paths using same OpenCode plugin/tool route, run-specific evidence. Keep demo data isolated and redacted in ordinary logs.  
**Deliverables:** Reproducible demo harness and independent sink verification.  
**Gate A3:** Real agent attempts exfiltration under controlled attack; OFF fake secret received; ON sink not invoked; event IDs match and same tool boundary used. Explicitly label detector mode **policy-only**, not Option A. If agent never attempts, result INCONCLUSIVE, not PASS.  
**On failure:** Iterate fixture and supported tool path; do not manufacture a sink call.

### A4 — Local API, event store, SSE, detector handshake
**Prerequisites:** A2 + C0. Can run in parallel with A3.  
**Tasks:** Loopback API and SSE, in-memory bounded event storage, redaction, run state endpoint, health/coverage and correlation IDs, detector-client HTTP transport, crash/reconnect/timeout; integrate B's service when B3 ready (C1).  
**Deliverables:** `@anchor-ai/server`, server tests, OpenAPI fidelity tests, diagnostic view.  
**Gate A4:** Actual runtime events stream in order; replayed fixture endpoints cannot masquerade as live; server interruption does not bypass policy; malicious cross-origin/missing auth is rejected where relevant; fail-closed boundary remains independent of UI.  
**On failure:** Keep core service usable with audit logs; do not allow UI to become policy authority.

### A5 — npm packages, CLI, configuration and external-consumer installation
**Prerequisites:** A1 + A2 + A4; A3 recommended.  
**Tasks:** Package exports/types, `npm pack`, plugin integration instructions, config loader/validation and overrides, `anchor init|doctor|serve|demo|status|logs`, version compatibility; verify distribution names/registry availability before publish.  
**Deliverables:** Packable npm workspace packages, sample external consumer, install docs; release remains unpublished until approval.  
**Gate A5:** Clean external directory installs tarballs and loads actual OpenCode plugin, executes one controlled gated action, works policy-only with **no Python installed**; invalid security config produces actionable failure.  
**On failure:** Fix package `files`/exports/CLI bins and dependencies before expanding SDK.

### A6 — Optional MCP adapter and advanced coverage
**Prerequisites:** A2 + A5. **Optional; never block Option A critical path.**  
**Tasks:** Adapter delegates to same `@anchor-ai/core`, verified controlled MCP tools and coverage tests; reject misleading claims about built-in tools or unrelated servers.  
**Deliverables:** `@anchor-ai/mcp`, setup guide, tool contract tests.  
**Gate A6:** MCP calls respect the identical state/policy/event schemas; genuine blocked side effect never executes; coverage documented.  
**On failure:** Defer without changing core release goals.

### A7 — Security hardening and release engineering
**Prerequisites:** A5 and C1; C2 for public Option A claims.  
**Tasks:** CI for TS, static checks, lockfile reproducibility, secret scan, scoped package checks, npm provenance/versioning/rollback; failure injection, concurrency and performance; consolidate release checklist.  
**Deliverables:** TS CI jobs, npm release dry run, security evidence.  
**Gate A7:** Fresh checkout build/test, `npm pack` contents audited, no model weights or demo secrets accidentally bundled, no unapproved publishing; stable test consumer and bounded permissions.  
**On failure:** Release blocked; local demo remains usable.

## 5. Developer B — seven independent phases

### B0 — Probe provenance and inference feasibility audit
**Prerequisites:** Access to existing Qwen assets, scripts, logs, model identifiers, hardware.  
**Tasks:** Inventory weights/revision/hash, tokenizer/template, layer/token position, Δ-state preprocessing, probe artifacts, threshold, precision, eval dataset, current Python dependencies. Check OpenCode provider/tool-call requirements and resource budgets.  
**Deliverables:** `docs/ml/probe-provenance.md`, `docs/ml/inference-feasibility.md`, B status log.  
**Gate B0:** Provenance matrix distinguishes verified from missing metadata; exact artifacts identified or gate marked BLOCKED; no default to approximate activations.  
**On failure:** Stop claims of compatible direct detection, preserve existing artifacts.

### B1 — Real Qwen endpoint and tool-call viability spike
**Prerequisites:** B0 + C0 provider/request IDs contract.  
**Tasks:** Python service loading pinned Qwen once; implement minimal validated OpenAI-compatible request path needed by actual OpenCode; test message roles, streaming if required, tool schema/selection/arguments, turn continuation and 2+ tool calls. Explicitly ensure OpenCode uses this endpoint, not external model fallback.  
**Deliverables:** Minimal server + smoke harness + provider config proof + latency/memory notes.  
**Gate B1:** Recorded real OpenCode model requests and successful real tool-call round trip; if model cannot robustly generate usable tool calls, mark B1 BLOCKED and document evidence. No fake/model-independent tool calls allowed.  
**On failure:** Research a faithful adapter/provider compatibility fix without silently changing model; bring blocking decision to C1/C2.

### B2 — Compatible same-generation hidden states and probe validation
**Prerequisites:** B0 and B1 inference path.  
**Tasks:** Instrument same model generation forward passes, map token/context boundaries, reconstruct exact training Δ-state from actual compatible activations, run pinned probe; reproduce offline fixtures with defined numerical tolerance; record model/feature/probe hashes and source inference request ID. Distinguish original generation states from an auxiliary second pass.  
**Deliverables:** `docs/ml/parity-report.md`, scoring module and tests, provenance fixtures and meaningful measured score output.  
**Gate B2:** Measured scores trace to exact live OpenCode generation requests with compatible extraction; offline parity within measured tolerance; score validity and timing verified. **An additional scoring forward pass does not satisfy same-generation gate.**  
**On failure:** Gate remains BLOCKED; do not call secondary pass “direct” or substitute shadow Qwen.

### B3 — Detector API, metadata, errors and isolated test harness
**Prerequisites:** B1, B2, C0.  
**Tasks:** Implement `/health`, `/metadata`, actual compatible model chat API and securely correlated activation/detector results; implement statuses `ready|unavailable|incompatible|error|timeout` as contract requires; limits, localhost binding, no raw secret logging; Python fixtures test even before A connects.  
**Deliverables:** Detector API tests and OpenAPI/JSON-schema validation; C1 ready integration instructions.  
**Gate B3:** All request/response fixtures validate; model/probe hash mismatches visibly fail; no fabricated scores; crash/timeout semantics correctly surfaced; A can integrate without Python source changes.  
**On failure:** Keep API out of enforce-ready mode until parity and contract tests pass.

### B4 — Dashboard UI built independently against event contracts
**Prerequisites:** C0; no need to wait for A runtime.  
**Tasks:** Build frontend views: overview/mode/coverage, live timeline, scores/provenance, taint state, policy decisions, sink results, sessions/run comparison, audit history and diagnostics. Use explicit `fixture` mode only in development, define empty/loading/error/SSE-disconnected states.  
**Deliverables:** `apps/dashboard`, UI component tests and accessibility checks.  
**Gate B4:** UI renders every contract-valid event and handles null scores, late events, reconnect, redaction; **fixture mode clearly marked**, never presented as live. Can build as static assets without Python.  
**On failure:** Trim polish; prioritize truthful timeline and connected/disconnected state.

### B5 — Live portal wiring, public docs and onboarding
**Prerequisites:** B4 and A4's SSE/API (for live wiring); A5 package contract (for install docs).  
**Tasks:** Connect UI to real loopback API and ordered events, real sink evidence; build docs site with installation, OpenCode integration, npm SDK, CLI, threat model/coverage, controlled demo, Option A inference/probe parity, caveats, config/REST reference and troubleshooting. Make static frontend build consumable by A's server without editing server source.  
**Deliverables:** Production frontend bundle + static docs site + clean-room walkthrough.  
**Gate B5:** UI updates from **actual** runtime events; score shown only when correlated genuine activation result; portal shows clear coverage and provider/model identity; docs site builds and instructions verified from fresh checkout.  
**On failure:** Release only minimal dashboard with documented limitations; do not fabricate telemetry.

### B6 — Evaluation, latency, resource and robustness evidence
**Prerequisites:** B2 + B3; C1 for combined timing.  
**Tasks:** Benign, injection, held-out and failure cases with transparent sample counts; record accuracy/false positives, end-to-end inference and scoring latency, memory, CPU/GPU precision, tool-call reliability; handle insufficient hardware explicitly.  
**Deliverables:** `docs/ml/evaluation-report.md`, machine-readable results and reproducible commands.  
**Gate B6:** Every metric linked to dataset/split/model/probe config, no sweeping production generalization claim; fail-closed tests and known limitations documented. Historical 0.998 AUROC never shown without evaluation caveats.  
**On failure:** Document measured gap and restrict claims; do not tune against held-out results without new evaluation split.

### B7 — Python service packaging and cross-platform startup
**Prerequisites:** B3 + B6; can partially overlap with B5.  
**Tasks:** Pin Python dependencies, reproducible venv/setup, model artifact download/cache policy, local service lifecycle/health, CPU startup instructions, optional Python distribution if justified, platform-specific diagnostics, no accidental shipment of large weights.  
**Deliverables:** Tested Python setup script, service start docs, optional Python package artifact (not mandatory PyPI publish).  
**Gate B7:** Fresh machine/clean environment reproducibly launches configured model+probe, reports metadata and readiness, handles missing assets with actionable errors; no secret exposure or accidental bundled weights.  
**On failure:** Block release claims for supported platforms, keep documented working reference platform.

## 6. Minimal interface contracts to freeze at C0

**Canonical IDs:** `runId`, `sessionId`, `toolCallId`, `inferenceRequestId`. IDs must be generated from actual integration context; use explicit mapping when OpenCode/provider IDs differ; no guessing joins by timestamp alone.

**Detector result fields (exact schema to finalize):** `schemaVersion`, `status`, `detectorMode`, `runId`, `inferenceRequestId`, `modelId`, `modelRevision`, `probeHash`, `featureExtractionHash`, `precision`, `layer`, `score` (number or null), `threshold` (number or null), `latencyMs`, `errorCode` (when relevant), `provenanceType` (`generation_forward_pass` or diagnostic alternate). The policy must reject incompatible/missing provenance in required Option A enforce mode.

**Security event fields (exact schema to finalize):** `schemaVersion`, `runId`, `sessionId`, `sequence`, `timestamp`, `kind`, `source`, `toolCallId?`, `inferenceRequestId?`, `detectorMode`, `taintState`, `verdict?`, `reasonCode?`, `score?`, `redacted`; null score rather than fake numeric values.

**Core API:** `observeToolResult(...)`, `evaluateBeforeAction(...)`, `startRun(...)`, `endRun(...)`; blocked action must be denied by verified plugin semantics. `DetectorClient` implementation belongs to A; Python detector implementation to B.

**Portal API:** Loopback `GET /api/health`, `GET /api/runs`, `GET /api/runs/:id/events`, `GET /api/coverage`, `GET /api/events/stream` (SSE). Final routes/schema agreed at C0; frontend cannot assume undocumented fields. Default auth/origin controls must prevent unrestricted local administrative actions.

**Contract evolution:** Only additive optional fields during v1 parallel development. Breaking changes require fixture migration, both owners' approval and a version bump. Include consumer-driven contract tests in both TS and Python CI.

## 7. Gate reporting and issue handoff protocol

Each phase PR must include the following filled template:

```md
## Phase: A2 (or B2)
- Owner:
- Preconditions and prerequisite gate references:
- Scope and files changed:
- Evidence (commands, test output, timestamps, screenshots/log paths):
- Gate result: PASS / BLOCKED / FAIL / INCONCLUSIVE
- What is verified vs merely planned:
- Interface/schema changes (must reference C0 PR):
- Remaining blockers and next phase:
- Reviewer and merge commit:
```

**Gate definitions:** PASS = demonstrated with reproducer and expected assertion; BLOCKED = external/prerequisite obstacle, not a substitute result; FAIL = assertion contradicted; INCONCLUSIVE = evidence insufficient. Only PASS unlocks mandatory dependent work. Cross-team review is required at C0, C1, C2 and for contract-breaking changes; other phases can be reviewed by peer asynchronously without both implementing the same module.

**Integration bug assignment:** If malformed detector response or wrong model score -> B; if correct detector verdict fails to block tool -> A; if correct event fails to render -> B; if A's SSE is missing/wrong -> A; if contract mismatch -> joint C0 change owner A for schema PR, B for Python fixture update. Avoid unowned bugs.

## 8. Parallel scheduling and milestone order

| Wave | Developer A | Developer B | Cross-team gate |
|---|---|---|---|
| 0 — audit | A0 audit hooks, repository | B0 audit probe & model | C0 freeze interfaces |
| 1 — prove feasibility | A1 plugin load, A2 gate | B1 Qwen OpenCode tool-call spike, B2 activations | No integration needed |
| 2 — deliver first proof | A3 controlled policy-only demo, A4 SSE/API | B3 detector API, B4 fixture-based UI | C1 service handshake |
| 3 — productize | A5 npm/CLI | B5 live portal/docs, B6 evaluation | C2 end-to-end Option A |
| 4 — harden | A7 release CI, optional A6 MCP | B7 Python reproducibility | Shared release approval |

**Do not distribute work by phase number in the old document** (e.g. A phases 0–5, B phases 6–11); that would force sequential dependencies. The tracks above proceed independently after C0.

**Critical gate precedence:** Successful agent tool call (B1) + generation-provenance parity (B2) are necessary for an authentic Option A demo. If they fail, preserve the A3 **policy-only** achievement as a narrower result, but do not promote it to C2.

## 9. Full-project definition of done

- [ ] Verified OpenCode plugin sees relevant real outputs and **blocks a protected action before its side effect** under the exact tested version.
- [ ] TypeScript npm package is consumable outside workspace, with clear protected/ungated coverage.
- [ ] Single TypeScript taint/policy authority, run isolation, fail-closed cases and audit events have passing tests.
- [ ] OpenCode **actually uses** Anchor-managed pinned Qwen2.5-0.5B inference to produce real tool calls.
- [ ] Detected score is correlated with **actual generation-forward-pass activations**, matching the trained probe preprocessing.
- [ ] Controlled OFF/ON use identical model/task/tools/secret and record independent fake-secret sink outcome; ON truly suppresses call.
- [ ] Local dashboard displays live events and honest unknown/unavailable detector states, not staged JSON.
- [ ] Public documentation explains installation, boundaries, evaluation limitations, and Option A dependencies.
- [ ] Failures, timeouts, probe mismatch and concurrent actions have regression tests.
- [ ] Fresh install works, release contents are audited, and publishing requires explicit owner approval.

## 10. Codex handoff prompts (one per developer)

**Developer A prompt:**
> Read `ANCHOR_PROJECT_HANDOFF_OPTION_A.md` and `ANCHOR_TWO_DEVELOPER_EXECUTION_PLAN.md`. You own A0–A7 only, plus shared C0/C1/C2 integration responsibilities. Start by auditing the current repo and OpenCode version. Do not edit B-owned Python/model/UI/docs folders. Produce `docs/status/dev-a.md`, an A0 coverage audit and a proposed C0 schema. Implement only phases whose prerequisites pass. All runtime authorization remains in TypeScript. Test pre-execution blocking with real sentinel evidence; do not call policy-only demo Option A. Never publish without approval.

**Developer B prompt:**
> Read `ANCHOR_PROJECT_HANDOFF_OPTION_A.md` and `ANCHOR_TWO_DEVELOPER_EXECUTION_PLAN.md`. You own B0–B7 only, plus shared C0/C1/C2 integration responsibilities. Start by auditing actual model/probe artifacts and OpenCode provider/tool-call requirements. Do not edit A-owned TypeScript core/plugin/policy/CLI/server. Implement the Anchor-managed Qwen endpoint, prove genuine OpenCode tool calling and exact **same-generation** hidden-state scoring before declaring B2 PASS. Build dashboard against C0 sample events until SSE exists, clearly labeling fixtures; connect to live A server in B5. Never substitute shadow scoring for Option A.

---

**Final principle:** Two distinct owners, one frozen wire contract, one security authority, and three planned integration checkpoints. Release readiness is decided by demonstrated gates—not by the number of features or lines of code.
