# Testing guide
MVP testing (`implementation_mvp.md`). Post-MVP test plan (fail-closed, Pipelock, live mode) lives with `implementation.md` and is added back when those phases start.

## Automated
- Full suite: `.claude/test-command` → `cd mvp && offline/.venv/Scripts/python -m pytest tests -q` (project venv: has fastapi + httpx for API tests). Tests read JSON/JSONL only; no torch imported. Artifact tests fail until the offline pipeline has run.
- Existing:
  - `test_design_mock.py` — `design/mock.html` has light + dark token sets for every colour family, plus the auto/light/dark switch.
  - `test_data.py` (Phase 1) — no doc in two splits; held-out from test docs only, paired one-to-one with benign-Hindi controls; length match; templates, benign and trigger sentences disjoint across train/val/test; insertion survives (no truncation); polite style has no keyword markers. 21 passing with the design tests.
  - `test_probe.py` (Phase 2) — features/scores cover every row; best layer on val; threshold is the smallest with val FPR ≤ 5 %; shuffled-label AUROC in [0.4, 0.6]; test/heldout/external metrics with counts; actions for all 9 scenarios; scenario 9 is a held-out Hindi miss; per-kind hard-negative false blocks count only hard-negative rows; `metrics.hijacked` = `actions.hijacked`.
  - `test_frontend.py` (Phase 4) — exact val threshold sent on load/reset; held-out cards keep injected/clean tag; no innerHTML/eval; theme follows system with manual override; UI reads only `/api/*`, no literal scores.
  - `tests/browser_check.js` (Phase 4, browser) — paste into DevTools on the running site (or run via Chrome automation): every scenario's verdict/BLOCKED/TAINTED/source badge equals `/api/run`, metrics table equals `/api/metrics`, badge, no horizontal scroll. Returns `{ok: true}`.
  - `test_readme.py` (Phase 5) — every cell of the README MVP results table and every number in its prose equals `offline/out/metrics.json`; screenshot file exists. Update the README block whenever the pipeline is re-run.
  - `test_check_gpu.py` (full product, Phase 0) — `check_gpu.py` runs and writes its report on a machine without CUDA.
  - `test_api.py` (Phase 3) — taint rule, verdicts per scenario, validation (404/422/413), no ML imports, every served number traced to `offline/out/`.
- Simulation: `cd mvp && offline/.venv/Scripts/python sim/simulate.py` (in-process) → `sim/report.json`; add `--url http://127.0.0.1:8000` to run the same sessions over HTTP against a running server → `sim/report_http.json`. Exits non-zero if the pass bar fails. Restart the server after code changes (no `--reload`). Results: `docs/user-sim-report.md`.
  - `test_sim.py` (Phase 4.5) — the sim's independent taint-rule oracle agrees with the API on every scenario at 7 thresholds; every invalid sim input gets a 4xx.
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

## Planned tests (full product, `implementation.md`)
- Model switch: every offline script runs end to end with `--model qwen0.5b` on CPU in CI-sized form before any 3B run; outputs carry `run_meta` (asserted).
- Precision match: scorer refuses a probe whose `run_meta` model/precision differs from the loaded model (test).
- Attack families: each generator keeps the document split and template split; held-out families never appear in train/val (pytest on `rows.jsonl`); invisible-Unicode rows really contain TAG/zero-width code points; split payloads are only injected when both halves are present.
- Control: length+position-only classifier AUROC reported; test fails if it is missing.
- Baselines: same rows, same validation split, same FPR targets for every detector (pytest on `out/baselines.json`); pinned model revisions recorded.
- Agent bench: Anchor's probe/threshold not fit on benchmark rows (assert); thresholds at 1 % FPR on each benchmark's benign outputs; our re-run baselines within a stated tolerance of the published numbers, else flagged.
- Scorer: fail closed on error/timeout; split-payload Δ uses earlier outputs; attribution sentences come from the input text.
- Live agent: vanilla vs Anchor on the same tools and turn cap; Anchor run never sends the secret when the scorer flags (test with a fake scorer at the boundary only); Pipelock in the path (outbound request without proxy fails).
- Live API: same hardening tests as the MVP API (body cap, strict models, headers) + rate limit and input length cap on `/api/score`; user-sim harness reused with `--url`.
- Site numbers: README + site tables checked against `out/*.json` (extends `test_readme.py`).

## Manual (live)
### Phase 1 — model and data
1. `cd mvp/offline && python -c "<smoke>"` (one forward pass) — expected: 25 hidden states, < 1 s, rendered prompt shows page inside `<tool_response>`.
2. Spot-read 10 injected + 5 benign-insertion rows in `rows.jsonl` — expected: natural text, correct labels.
### Phase 4 — frontend
1. `cd mvp && uvicorn api.index:app`, open `/` — expected: `REPLAY` badge, 9 scenarios, three columns, metrics match `out/metrics.json`.
2. Run `tests/browser_check.js` in the console → `ok: true`. Then at 375 px width (DevTools device mode; an iframe also works for measuring, but its `prefers-color-scheme` follows the parent, so don't judge the theme there) — expected: no horizontal scroll, no console errors.
3. Theme: clear `localStorage['anchor-theme']`, reload → follows the system; the toggle switches and persists.
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
