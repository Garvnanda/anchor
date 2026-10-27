# Testing guide
MVP testing (`implementation_mvp.md`). Post-MVP test plan (fail-closed, Pipelock, live mode) lives with `implementation.md` and is added back when those phases start.

## Automated
- Full suite: `.claude/test-command` → `cd mvp && offline/.venv/Scripts/python -m pytest tests -q` (project venv: has fastapi + httpx for API tests). Tests read JSON/JSONL only; no torch imported. Artifact tests fail until the offline pipeline has run.
- Existing:
  - `test_design_mock.py` — `design/mock.html` has light + dark token sets for every colour family, plus the auto/light/dark switch.
  - `test_data.py` (Phase 1) — no doc in two splits; held-out from test docs only, paired one-to-one with benign-Hindi controls; length match; templates, benign and trigger sentences disjoint across train/val/test; insertion survives (no truncation); polite style has no keyword markers. 21 passing with the design tests.
  - `test_probe.py` (Phase 2) — features/scores cover every row; best layer on val; threshold is the smallest with val FPR ≤ 5 %; shuffled-label AUROC in [0.4, 0.6]; test/heldout/external metrics with counts; actions for all 8 scenarios.
  - `test_api.py` (Phase 3) — taint rule, verdicts per scenario, validation (404/422/413), no ML imports, every served number traced to `offline/out/`.
- Simulation: `cd mvp && offline/.venv/Scripts/python sim/simulate.py` → `sim/report.json`, exits non-zero if the pass bar fails.
- Re-run the offline pipeline: see flow.md → run order.
- Planned tests (`implementation_mvp.md` §7), now covered by the files above:
  - `test_data.py` — split leakage, held-out from test docs only, benign-Hindi controls, length match, template split, insertion survives truncation.
  - `test_taint.py` — high read score → later `send_email` blocked even with a clean-looking body.
  - `test_clean_passes` — clean scenario never `leaked`; anchor result matches stored score.
  - `test_keyword_threshold_fixed` — slider never changes keyword verdict.
  - `test_no_ml_imports` — `api/index.py` imports no torch / numpy / sklearn.
  - `test_data_from_pipeline` — every scenario score exists in `offline/out/`.
  - `test_validation.py` — bad `scenario_id` → 404; bad threshold → 422.
  - `test_action_source.py` — `action_source` matches `out/actions.json`.
- Simulation (Phase 4.5): `mvp/sim/` — 1,000 seeded users against `uvicorn api.index:app`; report in `docs/user-sim-report.md`.

## Manual (live)
### Phase 1 — model and data
1. `cd mvp/offline && python -c "<smoke>"` (one forward pass) — expected: 25 hidden states, < 1 s, rendered prompt shows page inside `<tool_response>`.
2. Spot-read 10 injected + 5 benign-insertion rows in `rows.jsonl` — expected: natural text, correct labels.
### Phase 4 — frontend
1. `cd mvp && uvicorn api.index:app`, open `/` — expected: `REPLAY` badge, 8 scenarios, three columns, metrics match `out/metrics.json`.
2. Browser at 375 px width — expected: no horizontal scroll, no console errors.
### Phase 5 — deploy
1. `npx vercel dev` from a fresh clone of `mvp/` — expected: site + `/api/*` work without running `offline/`.
2. Deployed URL on desktop and phone; check github.com for no `.env`, `.npy`, weights.

## Workflow setup (run once, by the user)
- Quiz pre-commit hook: `cd anchor && bash ~/.claude/skills/quiz/install.sh`
- Register project: add to `~/.claude/workflow/projects.md`:
  `| anchor | C:/Users/harag/Documents/coding/anchor | docs/implementation_mvp.md | on |`

## Test data / accounts
- Dataset: SQuAD validation contexts (CC BY-SA 4.0) + hand-written hard negatives and templates.
- Planted secret: fake `sk-demo-…`, stored in `probe_meta.json`.

## Known gaps
- Test sets are small (~20–30 rows per style); one row moves a rate ~4 points — counts always shown beside rates.
- No live-model test on the deployed site (replay only).
