# Status / resume point
Updated 2026-10-29. Read this first when resuming.

Active plan: `docs/implementation_mvp.md` (same-day MVP). Post-MVP roadmap: `docs/implementation.md`.

## Phases (MVP)
| Phase | Status | Notes (what's left, who) |
|---|---|---|
| 1 — Model and data | done | committed `315ab33`; spot-read passed by user |
| 2 — Activations and probe | done | reviewer PASS on re-review 2026-10-29 (per-kind hard-negative fix); user cleared the planned stop |
| 3 — Scenarios and backend | done | reviewer PASS 2026-10-29; 9 scenarios (9 = held-out Hindi Anchor miss); security F1 high fixed, F4/F6 low in backlog |
| 4 — Frontend | done | reviewer PASS 2026-10-29 (re-ran browser_check.js headless at 375 px light/dark + 1280 px); user approved the look |
| 4.5 — User simulation | harness written, never run | run `sim/simulate.py`, write `docs/user-sim-report.md`, clear backlog, full security run |
| 5 — Deploy and submit | todo | README MVP section, metrics check script, `npx vercel dev`; push/import/submit are the user's |

## Measured results
`mvp/offline/out/metrics.json`; summary in decisions.md → "Phase 2 results". Layer 9, threshold 0.4313; test AUROC 0.998 (127/132) vs keyword 0.556 (31/132); held-out Hindi 12/22, benign-Hindi FB 2/22; InjecAgent 20/200 (AUROC 0.62) vs keyword 17/200; shuffled 0.494; model hijacked 2/6 demo scenarios.

## Repo state
- Commits: `315ab33` Phase 1, `c60f82e` Phase 2, `3062580` wip Phases 3–4.5 code. Not pushed.
- Phases 2–4 committed 2026-10-29 (see `git log`).
- After Phase 4.5: user wants to start the post-MVP roadmap `docs/implementation.md` (full project), not Phase 5 yet (2026-10-29).
- Gate: `.claude/test-command` → 91 passed.
- Pipeline re-run order (from `mvp/offline`): `train_probe → external_eval → gen_actions → build_scenarios` (extract reuses the feature cache; gen_actions ~10 min on CPU).
- `pip-audit` was installed into `mvp/offline/.venv` by the security run (dev-only, not in requirements).

## Known issues (from the removed scaffold — MVP must not repeat)
- Block decision scored on the email text, not the poisoned page → fixed by the taint rule.
- Last-token read without chat template → fixed: chat template, tool role, assistant-start.
- Norm score grew with output length → replaced by a trained probe; clean rows carry length-matched insertions.
- Silent fallback to mock → MVP shows `REPLAY` badge; no mock scorer exists.
