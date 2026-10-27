# Status / resume point
Updated 2026-10-28. Read this first when resuming.

Active plan: `docs/implementation_mvp.md` (same-day MVP). Post-MVP roadmap: `docs/implementation.md`.
Repo holds docs only; no code yet. Old scaffold deleted (its lessons: "Known issues" below).

## Phases (MVP)
| Phase | Status | Notes (what's left, who) |
|---|---|---|
| 1 — Model and data | manual → passed | reviewer PASS after fixes (3-way text split, paired held-out); spot-read passed by user; then `user_voice` style added → 984 rows; 23 data/design tests pass. Not yet committed. |
| 2 — Activations and probe | in progress | full offline chain running in background (extract → train_probe → external_eval → gen_actions → build_scenarios); feature cache by content hash |
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
None yet.

## Repo state
- Committed up to `83f0304` (pushed by user). Uncommitted: workflow fixes (CLAUDE.md, docs edits, QUESTIONS.md, security backlog, `.claude/test-command`, `.gitignore`).
- Gate: `.claude/test-command` → 3 passed (`mvp/tests/test_design_mock.py`).
