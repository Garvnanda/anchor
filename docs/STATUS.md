# Status / resume point
Updated 2026-10-28. Read this first when resuming.

Active plan: `docs/implementation_mvp.md` (same-day MVP). Post-MVP roadmap: `docs/implementation.md`.
Repo holds docs only; no code yet. Old scaffold deleted (its lessons: "Known issues" below).

## Phases (MVP)
| Phase | Status | Notes (what's left, who) |
|---|---|---|
| 1 — Model and data | todo | next; blocked on `docs/QUESTIONS.md` (RAM / internet) |
| 2 — Activations and probe | todo | incl. required `gen_actions.py` |
| 3 — Scenarios and backend | todo | security-breaker on `mvp/api` |
| 4 — Frontend | todo | visual approval (manual, user) |
| 4.5 — User simulation | todo | 1,000 simulated API sessions |
| 5 — Deploy and submit | todo | Vercel import, push, submission (manual, user) |

## Pending before/at resume
1. User answers `docs/QUESTIONS.md` (deadline, Vercel account, RAM/internet).
2. User runs the two blocked setup commands (quiz hook, project registration) — see testing.md → Workflow setup.
3. Start Phase 1: create `mvp/` layout, update `.gitignore`, venv, model smoke pass.

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
- Gate: `.claude/test-command` → no tests yet (pytest would collect 0; first Phase 1 item sets up the harness).
