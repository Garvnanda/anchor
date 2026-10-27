# Status / resume point
Updated 2026-10-28. Read this first when resuming.

Active plan: `docs/implementation_mvp.md` (same-day MVP). Post-MVP roadmap: `docs/implementation.md`.
Repo holds docs only; no code yet. Old scaffold deleted (its lessons: "Known issues" below).

## Phases (MVP)
| Phase | Status | Notes (what's left, who) |
|---|---|---|
| 1 — Model and data | manual → passed | reviewer PASS after fixes (3-way text split, paired held-out); spot-read passed by user; then `user_voice` style added → 984 rows; 23 data/design tests pass. Not yet committed. |
| 2 — Activations and probe | fix round done, in review | 1,434 rows; layer 9, thr 0.4313. Test AUROC 0.998, 127/132; all false-block groups ≤ 1/22. Held-out Hindi 12/22 with benign-Hindi FB 2/22. InjecAgent 20/200 (AUROC 0.62). Shuffled mean 0.494. Hijacked 2/5. 67 tests pass. Next: phase-reviewer → commit → report to user (planned stop). |
| 3 — Scenarios and backend | code written early | `build_scenarios.py`, `api/index.py`, `vercel.json`, `test_api.py` — not run until Phase 2 passes |
| 4 — Frontend | todo | visual approval (manual, user) |
| 4.5 — User simulation | todo | 1,000 simulated API sessions |
| 5 — Deploy and submit | todo | Vercel import, push, submission (manual, user) |

## Pending before/at resume
1. All questions answered (`docs/QUESTIONS.md`). Design mock `design/mock.html` (3 families × light/dark; serve with `py -3.12 -m http.server 8765` in `design/`) → user picks a family. Test harness live: `.claude/test-command` → 3 passed.
2. Optional: register project in `~/.claude/workflow/projects.md` (testing.md → Workflow setup). Quiz hook not needed (user override).
3. Start Phase 1: create `mvp/` layout, `py -3.12` venv, model smoke pass. Build straight through; planned stop after Phase 2.

## Known issues (from the removed scaffold — MVP must not repeat)
- Block decision scored on the email text, not the poisoned page → fixed by the taint rule.
- Last-token read without chat template → fixed: chat template, tool role, assistant-start.
- Norm score grew with output length → replaced by a trained probe; clean rows carry length-matched insertions.
- Silent fallback to mock → MVP shows `REPLAY` badge; no mock scorer exists.
- Tests covered the mock keyword filter only → §7 tests check taint logic, data splits, validation.

## Measured results
Phase 2 (2026-10-28), full numbers in `mvp/offline/out/metrics.json`; summary in decisions.md → "Phase 2 results".

## Repo state
- Phase 1 committed as `315ab33` (not pushed). Uncommitted: Phase 2–4.5 code written ahead (`offline/extract.py`, `train_probe.py`, `external_eval.py`, `gen_actions.py`, `scenario_pick.py`, `build_scenarios.py`, `api/`, `public/`, `sim/`, `tests/test_probe.py`, `tests/test_api.py`, `vercel.json`, `requirements.txt`).
- Resume: if the background pipeline died, re-run from `mvp/offline` in order `extract → train_probe → external_eval → gen_actions → build_scenarios` (extract reuses `features/cache.npz`). Then run the full test command, phase-reviewer for Phase 2, and stop for the user (planned).
- Gate: `.claude/test-command` → 3 passed (`mvp/tests/test_design_mock.py`).
