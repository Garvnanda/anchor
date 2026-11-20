# Testing guide
MVP testing (`implementation_mvp.md`). Post-MVP test plan (fail-closed, Pipelock, live mode) lives with `implementation.md` and is added back when those phases start.

## Automated
- Full suite: `.claude/test-command` → `cd mvp && offline/.venv/Scripts/python -m pytest tests ../v2/tests -q` (project venv: has fastapi + httpx for API tests). Tests read JSON/JSONL only; no torch imported. Artifact tests fail until the offline pipeline has run.
- Existing:
  - `test_design_mock.py` — `design/mock.html` has light + dark token sets for every colour family, plus the auto/light/dark switch.
  - `test_data.py` (Phase 1) — no doc in two splits; held-out from test docs only, paired one-to-one with benign-Hindi controls; length match; templates, benign and trigger sentences disjoint across train/val/test; insertion survives (no truncation); polite style has no keyword markers. 21 passing with the design tests.
  - `test_probe.py` (Phase 2) — features/scores cover every row; best layer on val; threshold is the smallest with val FPR ≤ 5 %; shuffled-label AUROC in [0.4, 0.6]; test/heldout/external metrics with counts; actions for all 9 scenarios; scenario 9 is a held-out Hindi miss; per-kind hard-negative false blocks count only hard-negative rows; `metrics.hijacked` = `actions.hijacked`.
  - `test_frontend.py` (Phase 4) — exact val threshold sent on load/reset; held-out cards keep injected/clean tag; no innerHTML/eval; theme follows system with manual override; UI reads only `/api/*`, no literal scores.
  - `tests/browser_check.js` (Phase 4, browser) — paste into DevTools on the running site (or run via Chrome automation): every scenario's verdict/BLOCKED/TAINTED/source badge equals `/api/run`, metrics table equals `/api/metrics`, badge, no horizontal scroll. Returns `{ok: true}`.
  - `test_check_deploy.py` (Phase 5) — `check_deploy.check()` passes on the real app and reports a metrics mismatch when the expected file differs.
  - `test_readme.py` (Phase 5) — README names the live URL; every cell of the README MVP results table and every number in its prose equals `offline/out/metrics.json`; screenshot file exists. Update the README block whenever the pipeline is re-run.
  - `test_check_gpu.py` (full product, Phase 0) — `check_gpu.py` runs and writes its report on a machine without CUDA.
  - `v2/tests/test_g1.py` (full product, G1) — committed `gpu_check.json` shows CUDA + 4-bit OK; `smoke_llama3b.json` has the G1 precision (NF4, bf16 iff supported), complete `run_meta`, 29 hidden states, ≥ 400-token page, ≥ 0.5 GB headroom, all rendered-prompt checks true, timings; `check_rendered` rejects a page in the user role / prompt not ending at assistant start; `run_gpu.md` carries the measured pass time.
  - Fresh clone: `test_probe.py` feature tests need `mvp/offline/features/*.npy` (git-ignored) — run `mvp/offline/extract.py` once (CPU, ~30 min) before the gate.
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

## Automated (full product, `v2/tests/`)
Run: `.claude/test-command` (runs `mvp/tests` then `v2/tests`, both with `mvp/offline/.venv`). Before the tests,
the qwen0.5b outputs must exist: from `v2/offline`, the pipeline with `--model qwen0.5b` (extract ~1.5 h on CPU for dataset v2)
(see `flow.md`), plus `python smoke.py`.
Do not run two copies of the v2 suite at once on the 16 GB laptop: `test_v2_extract_reproduces_the_seeded_mvp_cache`
loads Qwen, and two runs together hit `MemoryError` (seen 2026-10-30). The test reads only its 5 cache rows.
- `test_pipeline.py` (H0) — `--model/--precision` defaults and bad values; per-model folders; every script uses
  `parse(argv)`; every qwen output has `run_meta` (model, precision, device); `RunMismatch` on another
  model/precision for the probe loader and the feature cache; rows, metrics, scores, actions, scenarios equal the
  MVP's; v2 extract reproduces 5 seeded cache rows (loads Qwen, ~30 s); Qwen render equals the MVP render; Llama
  render has the fixed date and the insertion check accepts JSON-escaped text (needs the Llama tokenizer in the HF
  cache); env loader order; git-ignore of `.env`/features; API uses `anchor.policy`; `mvp/` has no uncommitted
  change; `run_gpu.md` lists the 3B steps; every committed `out/<model>/` (qwen now, llama3b after G2) is
  consistent (one model/precision per folder, layer best on val, val FPR ≤ target, shuffled AUROC in [0.4, 0.6],
  scores cover every row); `build_data` + `train_probe` re-run into `tmp_path` reproduce the stored qwen run (~40 s).
- `test_attacks.py` (H1) — v1 rows an unchanged prefix; every family in train/val/test (held-out ones only in
  `heldout`, from test docs); templates disjoint across splits; each injection has a control within ±10 % length;
  TAG / zero-width code points (decoded TAG text is the instruction); Cyrillic look-alikes; split halves in separate
  outputs; encoded payloads decode to the instruction; JSON families parse; tool_description in a tool description;
  exfil URLs only in injected rows; Tamil controls disjoint from the training pool; token budget.
- `test_pipeline.py` H1 additions — cache key unchanged for single-page rows; end index = last tool-output token
  (both tokenizers, ids equal the chat-template ids); an MVP-era cache is re-extracted; v1 start features equal
  the MVP cache; a fresh re-extract (prose, JSON, split payload, TAG) matches the cache at both positions.
- `test_kaggle.py` — notebook equals `make_notebook.render()` (regenerate after editing), cells parse, every
  `step("x.py")` exists in the run_gpu order, token only from Kaggle Secrets and never written or printed, zip
  excludes features and weights.
- Ported MVP tests (`test_api`, `test_data`, `test_probe`, `test_frontend`, `test_sim`, `test_check_gpu`,
  `test_gen_actions`, `test_check_deploy`) run against `v2/` and `out/qwen0.5b/`.

## Manual (full product)
- Kaggle: import `v2/kaggle/anchor_3b.ipynb`, set GPU T4 + Internet on, add secret `HF_TOKEN`, Run all. Expected:
  step 4 prints `hidden_states 29`; step 7 prints `run_meta: llama3b nf4 cuda` and the metrics; the zip is
  downloadable. Unzip into `v2/offline/`, run the tests, commit.

## Planned tests (full product, `implementation.md`)
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
0. After every deploy: `cd mvp && offline/.venv/Scripts/python sim/check_deploy.py https://anchor-nu-three.vercel.app` → `OK: … matches the offline run`. Optional load check: `sim/simulate.py --url <deployment>` (slow over the internet, 20+ min; do not run it at the same time as `check_deploy.py` — they compete and requests time out). A local uvicorn run cannot reproduce Vercel's routing (the 2026-10-29 rewrite bug passed locally).
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
