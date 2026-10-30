# Status / resume point
Updated 2026-10-30. Read this first when resuming.

Active plan (hook-tracked): `docs/implementation.md` (full product, H / G phases; headings `Phase <n> (H0)`). MVP Phase 5 manual items (phone check, walkthrough, submission) stay with the user, below.

## Phases (MVP)
| Phase | Status | Notes (what's left, who) |
|---|---|---|
| 1 — Model and data | done | committed `315ab33`; spot-read passed by user |
| 2 — Activations and probe | done | reviewer PASS on re-review 2026-10-29 (per-kind hard-negative fix); user cleared the planned stop |
| 3 — Scenarios and backend | done | reviewer PASS 2026-10-29; 9 scenarios (9 = held-out Hindi Anchor miss); security F1 high fixed, F4/F6 low in backlog |
| 4 — Frontend | done | reviewer PASS 2026-10-29 (re-ran browser_check.js headless at 375 px light/dark + 1280 px); user approved the look |
| 4.5 — User simulation | done | reviewer PASS 2026-10-29; sim 0 failures in-process and over HTTP (`docs/user-sim-report.md`); full security run 0 critical/high; backlog fixed or risk-accepted by user |
| 5 — Deploy and submit | live, partly manual | deployed https://anchor-nu-three.vercel.app (2026-10-29) after removing the `vercel.json` rewrite (API 404 bug); live metrics == file; GitHub tree clean; README has the URL. Left (user): phone check, walkthrough, submission |

## Measured results
`mvp/offline/out/metrics.json`; summary in decisions.md → "Phase 2 results". Layer 9, threshold 0.4313; test AUROC 0.998 (127/132) vs keyword 0.556 (31/132); held-out Hindi 12/22, benign-Hindi FB 2/22; InjecAgent 20/200 (AUROC 0.62) vs keyword 17/200; shuffled 0.494; model hijacked 2/6 demo scenarios.

## Phases (full product, `implementation.md`) — H0 built 2026-10-30
| Phase | Owner | Status | Head start from MVP | Waits on | Notes |
|---|---|---|---|---|---|
| H0 — Scaffold `v2/` + model switch + `run_gpu.md` | Haragam | manual (reviewer PASS; G line pending) | large | G line: run_gpu.md steps 1–2 on RTX 2050 or Kaggle | whole MVP copied; qwen run == MVP exactly; Kaggle notebook `v2/kaggle/anchor_3b.ipynb` |
| H1 — Attack families + dataset v2 (incl. Tamil) | Haragam | todo | medium | H0 | 8 new families, benign controls; manual spot-read by both |
| H2 — Baselines on our data (CPU) | Haragam | todo | small | H1 | PG2 22M/86M, Horizon guard, PIGuard, ProtectAI v2, Pipelock scanner, keyword, length+position control |
| H3 — Agent-benchmark sets (CPU) | Haragam | todo | none | H0 | rebuild AgentDojo/τ-bench/BIPIA sets; check PG2 22M vs published |
| H4 — Live scorer + playground API | Haragam | todo | medium | H0 | fail closed, attribution by measurement; security-breaker |
| H5 — Live agent loop + Pipelock | Haragam | todo | small | H4 | Pipelock v3.7.1 installed here (`~/tools/pipelock`); security-breaker |
| H6 — Black-box adaptive attacker (code) | Haragam | todo | none | H4 | runs on 0.5B here, on 3B in G5 |
| H7 — Evaluation report + replay data | Haragam | todo | medium | G2, H2, G3–G5 | every number from output files |
| H8 — Frontend redesign (Hallmark) + deploy | Haragam | todo | medium | H7 | security-breaker; manual look approval |
| H9 — User sim + security + pre-demo checks | Haragam | todo | large | H8, G7 | ≥ 1,000 users vs live server |
| H-X — Arc iGPU test (optional) | Haragam | todo | half | ≥ 7 GB free RAM, internet | half done: `torch 2.15.0+xpu` in a throwaway env |
| G1 — GPU setup + 3B smoke, confirm `nf4` (NF4 + fp16 compute) | Garv (+ Kaggle) | todo | medium | repo pulled, HF token | can start now: `check_gpu.py`; then `run_gpu.md` steps 1–2 once `v2/` is pushed |
| G2 — 3B activations + probe | Garv or Kaggle | todo | large (code) | G1, H1 | dry run on dataset v1 possible now (Kaggle notebook); proper run after H1 |
| G3 — Anchor-3B on agent benchmarks | Garv | todo | small | G2, H3 | frozen probe, 1 % FPR, comparable with arXiv 2610.03448 |
| G4 — 3B model actions + live agent runs | Garv | todo | small | G2, H5 | model-sourced leak, Pipelock layer logs |
| G5 — Adaptive attacks on 3B | Garv | todo | none | G2, H6 | black-box; GCG suffix stretch |
| G6 — Steering | Garv | todo (stretch) | none | G4 | |
| G7 — Live demo host | Garv | todo | small | G4, H8 | cold start ×2, network off |

## Repo state
- **2026-10-30, H0 built (uncommitted; user commits and pushes):** new `v2/` (offline pipeline with `--model/--precision`, per-model `data|features|out/<model>/`, `run_meta`, `RunMismatch`; `anchor/policy.py`; API/site/sim/tests copied; `offline/run_gpu.md`; `kaggle/make_notebook.py` + `anchor_3b.ipynb`). `.claude/test-command` now runs `mvp/tests` then `v2/tests`. `.gitignore` adds `v2/offline/features/`, `v2/offline/data/external/`. qwen0.5b outputs in `v2/offline/out/qwen0.5b/` (committed); features seeded from the MVP (`seed_from_mvp.py`, not committed).
- **H0 done except its manual G line** (reviewer PASS 2026-10-30): user pushes `v2/`, then Garv/Kaggle run `run_gpu.md` steps 1–2 (and the Kaggle notebook). Regenerating qwen outputs: from `v2/offline` with `../../mvp/offline/.venv/Scripts/python`: `seed_from_mvp.py → build_data → extract → train_probe → external_eval → gen_actions → build_scenarios`, `smoke.py`.
- **H1 in progress:** draft generators at `$CLAUDE_JOB_DIR/tmp/h1/attacks.py` (job temp dir; move into `v2/offline/attacks.py`). Decisions: tool_description held out with Hindi/Tamil; trained families on 3 of 4 main docs; also adds 1 %/5 % FPR thresholds and the last-token position for G2.
- **Next after H0:** H1 (attack families + Tamil), then H2/H3 (CPU), then H4–H6. User asked to keep going through all H phases, stopping only for questions or G blockers.
- Commits: `315ab33` Phase 1, `c60f82e` Phase 2, `3062580` wip Phases 3–4.5 code. Not pushed.
- Phases 2–4.5 committed 2026-10-29 (see `git log`). MVP is deploy-ready apart from the deferred Phase 5 items.
- After Phase 4.5: user wants to start the post-MVP roadmap `docs/implementation.md` (full project), not Phase 5 yet (2026-10-29).
- Full product planned 2026-10-29: `docs/implementation.md` = phases **H0–H9, H-X** (Haragam, CPU laptop, all code + 0.5B tests) and **G1–G7** (Garv, RTX 2050, all 3B runs), dependency map at the top. `mvp/` frozen; new code in a new folder (`v2/`, named at H0). Design `technical.md`, rationale `decisions.md`, open items `QUESTIONS.md`.
- Measured 2026-10-29: 3B cannot run on Haragam's CPU (no native bf16; bf16 matmul ~380× slower than fp32). Arc iGPU test (H-X) half done: `torch 2.15.0+xpu` in a throwaway env; stopped for low RAM + network drop.
- Next: (1) deploy the MVP (`implementation_mvp.md` Phase 5); (2) core work 2026-10-30: Garv starts G1 (`mvp/offline/check_gpu.py`), Haragam starts H0.
- Tools installed globally 2026-10-29: NVIDIA SkillSpector (`uv tool`), skills `skill-inspector` and `hallmark`; global `~/.claude/CLAUDE.md` now requires scanning skills before install and running Hallmark on frontend work.
- Gate: `.claude/test-command` → 124 passed.
- Pipeline re-run order (from `mvp/offline`): `train_probe → external_eval → gen_actions → build_scenarios` (extract reuses the feature cache; gen_actions ~10 min on CPU).
- `pip-audit` was installed into `mvp/offline/.venv` by the security run (dev-only, not in requirements).

## Known issues (from the removed scaffold — MVP must not repeat)
- Block decision scored on the email text, not the poisoned page → fixed by the taint rule.
- Last-token read without chat template → fixed: chat template, tool role, assistant-start.
- Norm score grew with output length → replaced by a trained probe; clean rows carry length-matched insertions.
- Silent fallback to mock → MVP shows `REPLAY` badge; no mock scorer exists.
