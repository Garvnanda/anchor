# Implementation plan — full product (two people, two laptops)

> **Active, hook-tracked plan since 2026-10-30** (MVP deployed; its Phase 5 manual items are in `STATUS.md`).
> Headings read `Phase <n> (H0)` because the workflow hook counts only `Phase <digit>` headings; the H/G name in
> brackets is the phase's real name. Design: `technical.md`. Decisions:
> `decisions.md` ("Full product", 2026-10-29). Open questions: `QUESTIONS.md`.

## Ground rules
- **Folders:** `mvp/` is frozen as shipped (deployed replay site). All new code lives in a new top-level folder,
  **`v2/`** (name confirmed by the user, 2026-10-30). `v2/` mirrors the MVP layout: `v2/offline/`,
  `v2/anchor/` (scorer, policy), `v2/agent/`, `v2/api/`, `v2/public/`, `v2/tests/`, `v2/sim/`. MVP code is copied
  in and changed there, never edited in `mvp/`.
- **Who:** **H** = Haragam (Intel Core Ultra 7 155H, 16 GB, Arc iGPU, no usable CPU bf16 — measured).
  **G** = Garv (Intel Core i5-H, RTX 2050 4 GB). Phases are named `H1, H2, …` and `G1, G2, …`.
- **Split by machine strength:** H builds and tests all code end to end with **Qwen2.5-0.5B on CPU**, and runs
  everything that needs no 3B model (data, attack generators, CPU baselines, benchmark-set rebuild, server, site,
  simulation, security). G runs **every Llama-3.2-3B step** on the RTX 2050 (activations, probe, agent runs,
  adaptive attacks, live demo host), using commands H writes in `v2/offline/run_gpu.md`.
- **Second 3B machine: Kaggle, ruled out 2026-10-30** (T4 failed the bf16 check, `decisions.md`). Every 3B step
  runs on Garv's RTX 2050. Original plan, kept for the record: **Kaggle (user, 2026-10-30).** H runs the heavy batch 3B steps (G1 smoke, G2, G3, G5) on a
  Kaggle T4 with `v2/kaggle/anchor_3b.ipynb`, which runs the same `run_gpu.md` steps. Whoever runs a G phase
  commits its `out/llama3b/` files; if only Garv's laptop is used, nothing changes.
  Split (user, 2026-10-30): **Kaggle** = G1 smoke on T4, G2, G3, G5, G4 model actions; **Garv's laptop (Windows)** =
  G1 check + smoke, G4 live agent runs, G7 demo host. Garv's laptop is the fallback for any Kaggle step.
- **Per-model folders:** every script writes under `data/<model>/`, `features/<model>/`, `out/<model>/`
  (`<model>` = `qwen0.5b` or `llama3b`), so the 0.5B and 3B runs never overwrite each other (see `run_gpu.md`).
- **One 3B setup:** the probe is trained and served with the same model build and precision: `nf4` = 4-bit NF4
  weights, **bf16 compute**, no double quant (G1 on the RTX 2050, user kept bf16). The Kaggle T4 failed the bf16
  check, so every 3B step runs on Garv's laptop.
  Scripts refuse features or a probe whose `run_meta` precision differs. The Arc test (H-X) may add a machine
  only with the identical precision.
- **Hand-off:** through git. Each side commits its outputs (`v2/offline/out/*.json`, never `.npy`, weights or
  `.env`); the other pulls. A G phase is "done" only when its output files are in the repo and pass the tests H
  wrote for them. Claude never pushes; each person pushes their own commits.
- **Gate for every phase (workflow):** tests for every new behaviour, `.claude/test-command` green with 0 skipped,
  `phase-reviewer` PASS; docs updated in the same change (`decisions.md`, `flow.md`, `testing.md`, `STATUS.md`).
  Phases that add attack surface (H4, H5, H8) also need `security-breaker` with no open critical/high. Frontend
  work runs the `hallmark` skill. H9 is the user simulation (≥ 1,000 users) before release.
- **Timebox:** core work 2026-10-30. Order below = build order; **(stretch)** phases are cut first.

Status values (hook format): `todo` · `done` · `manual` · `blocked`.

## Dependency map
```
H0 scaffold ─┬─► H1 attacks/data ─┬─► G2 3B probe ─┬─► G3 agent-bench scoring ─┐
             │                    │                ├─► G4 3B agent + hijack    ├─► H7 report ─► H8 site ─► H9 checks
G1 GPU setup ┘                    ├─► H2 baselines ┘   (needs H5 code)         │
                                  └─► H3 bench sets ──► G3                     │
H4 live scorer/server ─► H5 agent + Pipelock ─► G4 ─► G7 live demo host ───────┤
H6 adaptive attacker code ─► G5 adaptive runs on 3B ──────────────────────────┘
G6 steering (stretch, after G4)        H-X Arc iGPU test (optional, any time)
```

---

## Haragam (H) — Core Ultra 7, CPU, 0.5B dev model

### Phase 1 (H0) — Scaffold `v2/` and the model switch
**Status**: manual
**Progress (2026-10-30):** built. Whole MVP copied into `v2/` (offline pipeline, API → `anchor/policy.py`, site,
sim, tests). `--model/--precision`, `run_meta`, per-model folders, mismatch refusal, `run_gpu.md` and the Kaggle
notebook are in place. The qwen0.5b run equals the MVP exactly (rows, layer 9, threshold 0.431316, all 1,434
scores). The qwen feature cache was seeded from the MVP's (seed script removed in H1); a test re-extracts sample rows with
v2 code. `phase-reviewer` PASS 2026-10-30 (its 4 non-blocking notes fixed). Left (manual): the G line — Garv or
Kaggle runs `run_gpu.md` steps 1–2 after the user pushes `v2/`.
**Reuse (head start: large):** whole offline pipeline (`mvp/offline/common.py`, `build_data.py`, `templates.py`, `extract.py` with content-hash feature cache, `train_probe.py`, `external_eval.py`, `gen_actions.py`, `scenario_pick.py`, `build_scenarios.py`), taint rule (`mvp/api/index.py` `run_defence`) and its tests, 127 tests as templates, `.claude/test-command` pattern. New: `--model`/precision switch, `run_meta`, `run_gpu.md`.
**Prerequisites:** MVP deployed or deploy-ready (`implementation_mvp.md` Phase 5); folder name confirmed.
**Deliverables:** `v2/` layout; MVP offline pipeline copied in (`common`, `build_data`, `extract`, `train_probe`,
`external_eval`, `gen_actions`, `templates`); `--model {qwen0.5b,llama3b}` and a precision setting on every script;
`run_meta` (model, precision, device, versions, date) in every output; shared taint rule in `v2/anchor/policy.py`;
`v2/offline/run_gpu.md` (ordered, resumable 3B commands, expected runtimes, files to bring back); `.claude/test-command`
covering `v2/tests`; `.gitignore` entries for `v2/` artifacts.
**Done when**:
- [x] `v2/` runs end to end with `--model qwen0.5b` on CPU (build_data → extract → train_probe) and its numbers match the MVP's within rounding (same model, same data) — test.
- [x] Every output carries `run_meta`; the probe loader refuses a `run_meta` model/precision different from the loaded model — tests.
- [x] `policy.py` passes the MVP taint tests (ported).
- [ ] `run_gpu.md` lists G2–G5 commands (test); G confirms they run: G1 used Garv's own `smoke_llama3b.py`, so the v2 pipeline's `smoke.py --model llama3b` (run_gpu.md step 2) is still to run on the RTX 2050 or Kaggle.
- [x] `mvp/` unchanged (`git diff --stat mvp/` empty for this phase).

### Phase 2 (H1) — Attack families and dataset v2
**Status**: todo
**Reuse (head start: medium):** `build_data.py` + `templates.py` (document split, train/val/test template split, length-matched benign insertions, held-out Hindi with paired benign controls, hard negatives, JSON tool responses) and `test_data.py` (split/leak/length tests). New: the 8 family generators, Tamil, their benign controls.
**Prerequisites:** H0.
**Deliverables:** `v2/offline/attacks.py` generators (encoded, invisible_unicode, homoglyph, split_payload,
tool_description, rag_document, Tamil held out with benign-Tamil controls, exfil_link) wired into `build_data.py`;
`rows.jsonl` + `data_summary.json` v2. Added for G2 (H writes all code): two read positions in `extract.py`
(assistant start, last tool-output token) and thresholds at 5 % and 1 % val FPR in `train_probe.py`.
**Progress (2026-10-30):** generators + build done (2,872 rows: 1,434 v1 prefix unchanged + 698 family pairs;
held out: Hindi, Tamil, tool_description). Qwen re-extract (both positions) running; then train_probe →
external_eval → gen_actions → build_scenarios, tests, phase review, push #2.
**Done when**:
- [ ] Every family present with counts per split; held-out families (Hindi, Tamil, + any family chosen as held out) only in test/heldout (pytest).
- [ ] Invisible-Unicode rows contain TAG / zero-width code points; homoglyph rows contain non-ASCII look-alikes; split payloads have both halves in separate outputs (pytest).
- [ ] Each new format has length-matched benign controls (±10 %) (pytest).
- [ ] No document in two splits; train/val/test templates disjoint (MVP tests ported and passing).
- [ ] (manual) Haragam and Garv spot-read 2 rows per new family.

### Phase 3 (H2) — Baselines on our data (CPU)
**Status**: todo
**Reuse (head start: small):** MVP keyword baseline + metric code in `train_probe.py` (`threshold_at_fpr`, `evaluate`, counts beside rates); Pipelock v3.7.1 installed (`~/tools/pipelock`). New: loading/running 6 detectors, length+position control.
**Prerequisites:** H1. Runs in parallel with G2.
**Deliverables:** `v2/offline/baselines.py` → `out/baselines.json`: Prompt Guard 2 22M + 86M, Horizon-Labs
guard-base (pinned revision), PIGuard, ProtectAI v2, Pipelock response scanner (v3.7.1, unmodified), MVP keyword
list, length+position-only control.
**Done when**:
- [ ] Same rows, thresholds from val only at 1 % and 5 % FPR, for every detector (pytest).
- [ ] Per split and per family: TPR with counts, false blocks on clean / hard negatives / benign controls, AUROC.
- [ ] Licence, model revision and known training-data overlap recorded per detector.
- [ ] Length+position control AUROC reported (it is the "is the probe cheating" check for G2).

### Phase 4 (H3) — Agent-benchmark sets (CPU)
**Status**: todo
**Reuse (head start: none):** nothing in the repo; `lzwhehe/benign-instruction-bench` (MIT) provides the rebuild scripts. InjecAgent loader in `external_eval.py` is a pattern.
**Prerequisites:** H0. Independent of H1.
**Deliverables:** `v2/offline/agentbench_sets.py`: rebuild AgentDojo, τ-bench and BIPIA tool-output sets with
`lzwhehe/benign-instruction-bench` (steps 1–3, `PYTHONHASHSEED=0`); re-run Prompt Guard 2 22M (+1 detector) on
them; `out/agentbench_sets.json` (counts, hashes) for G3.
**Done when**:
- [ ] Set sizes and content hashes recorded; rebuild is deterministic (re-run gives same hashes).
- [ ] Our Prompt Guard 2 22M TPR at 1 % FPR within a stated tolerance of the published 60.9 % (AgentDojo) / 60.8 % (τ-bench), or the gap explained.
- [ ] Sets never used for training or threshold choice (assert in G3 code + test).

### Phase 5 (H4) — Live scorer and playground API
**Status**: todo
**Reuse (head start: medium):** prompt building + Δ at assistant start (`common.py`, `extract.py`), hardened FastAPI app (`mvp/api/index.py`: BodyCap, strict models, 422 handler, headers in `vercel.json`) and its tests. New: model kept in memory, `/api/score`, attribution, rate limit.
**Prerequisites:** H0.
**Deliverables:** `v2/anchor/scorer.py` (model + probe loaded once, Δ with earlier outputs, fail closed, attribution);
`v2/api/` live FastAPI (`/api/health` with `mode: live|replay` + `run_meta`, `/api/score`), MVP hardening reused,
rate limit + input cap; attribution method chosen by measurement (cheap projection vs leave-one-sentence-out).
**Done when**:
- [ ] All scorer behaviour tested with 0.5B: fail closed on error/timeout, split-payload Δ uses earlier outputs, attribution spans come from the input text.
- [ ] Attribution: cheap method's agreement with leave-one-out measured on ≥ 50 val rows; method chosen and recorded.
- [ ] MVP API hardening tests ported and passing; rate limit and input cap tested.
- [ ] `security-breaker` on `v2/api`: no open critical/high.

### Phase 6 (H5) — Live agent loop with Pipelock
**Status**: todo
**Reuse (head start: small):** action prompt + lenient JSON parser + hijack check (`gen_actions.py`, `test_gen_actions.py`), taint rule. New: multi-turn loop, tools, mock web/mail, Pipelock wiring.
**Prerequisites:** H4; Pipelock v3.7.1 (`~/tools/pipelock/`, checksum-verified; G installs the same version).
**Deliverables:** `v2/agent/`: multi-turn loop (`fetch_page`, `read_file`, `search_kb`, `list_tools`, `send_email`),
local mock web + mailbox, vanilla and Anchor variants sharing code, turn cap, per-run layer log; outbound through
Pipelock (fetch proxy for pages, forward proxy for mail); `/api/agent/run`.
**Done when**:
- [ ] Loop tested with 0.5B and with a fake scorer at the boundary only: tainted run never sends the side effect; both variants stop at the turn cap.
- [ ] Pipelock in the path: outbound without the proxy fails; Pipelock blocks a direct secret-exfiltration request with Anchor off (test against the real binary).
- [ ] Logs say which layer stopped which attack.
- [ ] `security-breaker` on `v2/agent` + `v2/api`: no open critical/high.

### Phase 7 (H6) — Black-box adaptive attacker (code)
**Status**: todo
**Reuse (head start: none):** nothing; uses H4's scorer.
**Prerequisites:** H4.
**Deliverables:** `v2/offline/adaptive.py`: rewrite loop (paraphrase, voice, position, encoding) against the
scorer's yes/no output; query budget; works with any `--model`; GCG suffix entry point stub for G5 only if G5 is in scope.
**Done when**:
- [ ] Runs end to end on 0.5B on ≥ 20 held-out injections; output `out/adaptive.json` schema tested.
- [ ] Attack success counted only if the rewritten injection still carries the attacker's goal (check tested).

### Phase 8 (H7) — Evaluation report and replay data
**Status**: todo
**Reuse (head start: medium):** `build_scenarios.py`, `test_readme.py`, `test_data_from_pipeline` pattern (every number traced to a file), README results block.
**Prerequisites:** G2, H2, G3, G4, G5 (whatever finished).
**Deliverables:** `v2/offline/report.py` → `out/report.json` + markdown: attack grid (family × defence), baselines,
agent-bench table (published numbers labelled as arXiv 2610.03448), adaptive results, latency/memory; replay data
copied to `v2/api/data/`.
**Done when**:
- [ ] One command builds every table the site and README show; every number traces to a G/H output file (test, extends the MVP's `test_readme.py` / `test_data_from_pipeline`).
- [ ] Prior art cited (TaskTracker, Attention Tracker, arXiv 2610.18408, 2602.00750, 2610.03448).
- [ ] Results reported whichever way they went (losses included).

### Phase 9 (H8) — Frontend redesign and deploy
**Status**: todo
**Reuse (head start: medium):** `mvp/public/` (vanilla JS, theme tokens, mode badge, light/dark), `tests/browser_check.js`, `test_frontend.py`, Vercel config + security headers. Redesign replaces the layout.
**Prerequisites:** H7.
**Deliverables:** `v2/public/` redesigned with the `hallmark` skill: run story, drift gauge, highlighted sentences
(playground), attack grid, comparison tables, less text; one frontend for live and replay mode; Vercel replay deploy
of `v2/`; optional tunnel bridge to the live laptop (stretch).
**Done when**:
- [ ] Hallmark build/audit run and its gates pass; (manual) Haragam approves the look.
- [ ] Browser check script (ported) passes: numbers equal the API, 375 px, light/dark, no console errors.
- [ ] Fresh-clone Vercel deploy of `v2/` works; every number matches `out/*.json`.
- [ ] Tunnel bridge with rate limit + `security-breaker` pass. (stretch)

### Phase 10 (H9) — User simulation, security, pre-demo checks
**Status**: todo
**Reuse (head start: large):** `mvp/sim/simulate.py` (in-process + `--url`, independent taint oracle), `test_sim.py`, user-sim report format, security backlog process.
**Prerequisites:** H8, G7.
**Done when**:
- [ ] `v2/sim/simulate.py` (ported) with ≥ 1,000 users against the live server on G's laptop (`--url`) and the replay deploy; pass bar met; `docs/user-sim-report.md` updated.
- [ ] `security-breaker` full-project run: 0 open critical/high; backlog cleared.
- [ ] Demo runs with the network off except localhost (fonts self-hosted or fallback verified).
- [ ] Secret scan clean; full test suite green, 0 skipped.

### Phase 11 (H-X) — Arc iGPU test (optional)
**Status**: todo
**Reuse (head start: half):** `torch 2.15.0+xpu` installed in a throwaway env; test script `spike_xpu.py` written; blocked by RAM/network on 2026-10-29.
**Prerequisites:** ≥ 7 GB free RAM, internet (spike half done 2026-10-29: `torch 2.15.0+xpu` installed in a throwaway env).
**Done when**:
- [ ] fp32/fp16/bf16 matmul speed and one 3B scoring pass timed on the Arc iGPU; recorded in `decisions.md`; decides whether H's laptop can be a second 3B machine (same precision as G1 only).

---

## Garv (G) — RTX 2050 (4 GB), i5-H, all Llama-3.2-3B runs

### Phase 12 (G1) — GPU setup and 3B smoke
**Status**: done
**Reuse (head start: medium):** `mvp/offline/check_gpu.py` (+ test) ready to run; `smoke.py` pattern for the 3B smoke.
**Prerequisites:** repo pulled; HF token with Llama access in `v2/offline/.env` (git-ignored; Garv's own token or Haragam's shared privately).
**Deliverables:** `v2/offline/out/gpu_check.json` (`check_gpu.py`: CUDA, bf16 support, VRAM, bitsandbytes 4-bit;
Kaggle writes `gpu_check_kaggle.json`); `v2/offline/out/llama3b/smoke.json` (hidden-state count, time per pass,
rendered prompt check); precision confirmed.
**Done when**:
- [x] `gpu_check.json` and `smoke_llama3b.json` committed (`v2/offline/out/`); 3B runs with ≥ 0.5 GB VRAM headroom on a 400-token page (1.354 GB measured).
- [x] Precision fixed (NF4 + bf16 compute, measured; expected: 4-bit NF4 weights, bf16 compute if `bf16_supported`, else fp16) and recorded in `decisions.md`; `QUESTIONS.md` 3B item closed.
- [x] Time per pass recorded (0.8305 s); G2 runtime estimated in `run_gpu.md` (~14 min / 1,000 rows).

### Phase 13 (G2) — 3B activations and probe
**Status**: todo
**Reuse (head start: large (code)):** `extract.py` + `train_probe.py` do this end to end on 0.5B; only the 3B run, more layers, the position comparison and the 1 % FPR threshold are new.
**Prerequisites:** G1, H1.
**Deliverables (run `run_gpu.md` steps):** Δ features for all v2 rows (kept local, not committed); `out/probe.json`,
`metrics.json`, `layer_sweep.json`, `scores.json` with `run_meta`; layer sweep over a spread of the 28 layers;
assistant-start vs last-token position comparison; thresholds at 1 % and 5 % val FPR; shuffled-label control.
**Done when** (checked by H's tests on the committed files):
- [ ] Every row scored; layer and position chosen on val only, with the comparison recorded in `decisions.md`.
- [ ] Shuffled-label AUROC in [0.4, 0.6]; length+position control (H2) clearly below the probe — or the result reported as a shortcut.
- [ ] TPR at 1 % / 5 % FPR on test, Hindi, Tamil and every attack family, counts beside rates.

### Phase 14 (G3) — Anchor-3B on the agent benchmarks
**Status**: todo
**Reuse (head start: small):** frozen-probe scoring pattern from `external_eval.py`.
**Prerequisites:** G2, H3.
**Deliverables:** `out/agentbench.json`: frozen probe scored on AgentDojo, τ-bench, BIPIA sets; TPR at 1 % FPR on each
benchmark's benign outputs; AUROC; bootstrap intervals.
**Done when**:
- [ ] Set hashes match H3's; probe/threshold untouched (run_meta + hash check, tested).
- [ ] Anchor row comparable with the published table (same protocol); result reported whichever way it goes.

### Phase 15 (G4) — 3B model actions and live agent runs
**Status**: todo
**Reuse (head start: small):** `gen_actions.py` (3B run is a flag change); agent loop comes from H5.
**Prerequisites:** G2, H5.
**Deliverables:** 3B `gen_actions` on the demo pages; hijack rate; live agent runs (vanilla vs Anchor, Pipelock on)
over the demo pages and a sample of each attack family → `out/agent_runs.json` with per-run layer logs.
**Done when**:
- [ ] Vanilla 3B agent leaks the key by itself (model-sourced, not scripted) on ≥ 1 page; hijack rate recorded.
- [ ] Anchor agent blocks every tainted side effect in the runs; misses listed with their scores.
- [ ] Pipelock stops the exfil_link family with Anchor off; layer attribution logged.

### Phase 16 (G5) — Adaptive attacks on 3B
**Status**: todo
**Reuse (head start: none):** runs H6's code; GCG suffix is new.
**Prerequisites:** G2, H6.
**Deliverables:** black-box rewrite attack on the 3B scorer (`out/adaptive.json`); white-box multi-probe GCG suffix
(arXiv 2602.00750) if VRAM allows **(stretch)**; suffix-augmentation defence **(stretch)**.
**Done when**:
- [ ] Black-box: attack success vs queries on ≥ 50 held-out injections, committed.
- [ ] White-box: evasion rate, or the reason it could not run on 4 GB recorded. (stretch)

### Phase 17 (G6) — Steering (stretch)
**Status**: todo
**Reuse (head start: none):** nothing built.
**Prerequisites:** G4.
**Done when**:
- [ ] Steering vector (mean difference at the probe layer) + forward hook; strength tuned on val.
- [ ] Measured on the live loop: attack success lower than block-free, user's task still completed; default `ANCHOR_MODE` recorded.

### Phase 18 (G7) — Live demo host
**Status**: todo
**Reuse (head start: small):** same server as H4/H5; MVP cold-start/browser checks as patterns.
**Prerequisites:** G4, H8.
**Done when**:
- [ ] Live server (`v2/api`) runs on G's laptop with the G1 precision; `/api/score` and `/api/agent/run` latency recorded.
- [ ] Demo works twice in a row from a cold start, network off except localhost.
- [ ] (manual) 60-second walkthrough rehearsed by both.

---

## Carried over from the MVP (met, reused in `v2/`)
- Taint rule + block decision (`mvp/api/index.py` `run_defence`, tests) → `v2/anchor/policy.py` (H0).
- Chat-template read at the assistant-start token with the page in the tool role (`mvp/offline/common.py`, `extract.py`).
- Dataset v1: document split, held-out Hindi with benign controls, hard negatives, JSON tool responses (1,434 rows).
- Probe pipeline (layer sweep, val threshold, shuffled control), InjecAgent external check, model-action generator and parser.
- Hardened FastAPI app, security headers, browser check, 1,000-user simulation harness, README number tests.
- Secret scan clean (security run 2026-10-29).
