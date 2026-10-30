# Code flow
Update whenever an entry point or data path changes. MVP layout from `implementation_mvp.md` §2: rows marked `exists` are shipped. Full-product additions (`implementation.md`, `technical.md`) are listed under **Planned (full product)** below until built.

## Entry points
| Command / route | What starts here | Status |
|---|---|---|
| `mvp/offline/check_gpu.py` | capability check for the 3B machine: CUDA, bf16/fp16 support + matmul speed, free VRAM, bitsandbytes 4-bit → `out/gpu_check.json` | exists |
| `v2/offline/check_gpu.py` | G1: same check (copy of the MVP script) on the RTX 2050 → `v2/offline/out/gpu_check.json` | exists |
| `v2/offline/smoke_llama3b.py` | G1: Llama-3.2-3B NF4/bf16 on CUDA; tool-role (`ipython`) prompt with fixed `date_string`; 5 timed passes on a 400-token page, peak VRAM, headroom, repeat-pass equality → `v2/offline/out/smoke_llama3b.json` | exists |
| `mvp/offline/smoke.py` | load model, one tool-role forward pass → `out/smoke.json` | exists |
| `mvp/offline/build_data.py` | SQuAD docs + injections + hard negatives → `offline/data/rows.jsonl`, `out/data_summary.json` | exists |
| `mvp/offline/extract.py` | rows → Δ activations per layer → `offline/features/delta_L{n}.npy` | exists |
| `mvp/offline/train_probe.py` | probe per layer, threshold, keyword baseline, shuffled control → `out/probe.json`, `metrics.json`, `layer_sweep.json`, `scores.json` | exists |
| `mvp/offline/external_eval.py` | frozen probe on InjecAgent → `external` block in `metrics.json`, `out/external_scores.json` | exists |
| `mvp/offline/gen_actions.py` | model picks next action per demo scenario → `out/actions.json` | exists |
| `mvp/offline/build_scenarios.py` | 9 test/heldout scenarios (incl. one held-out Anchor miss, picked by score < threshold) + scores → `out/scenarios.json`, `probe_meta.json`; copies JSON into `api/data/` | exists |
| `GET /api/health` | mode, model, layer, threshold, built_at | exists |
| `GET /api/scenarios` | scenario list | exists |
| `POST /api/run` | three defence traces for one scenario + threshold | exists |
| `GET /api/metrics` | metrics + layer sweep | exists |
| `mvp/public/index.html` | site UI, calls `/api/*` | exists |
| `mvp/sim/check_deploy.py <url>` | Phase 5: live deployment vs offline run — endpoints 200, `/api/metrics` == `offline/out/metrics.json`, every scenario's verdicts == independent oracle, bad input rejected; exits non-zero on mismatch | exists |
| `mvp/sim/simulate.py` | Phase 4.5: 1,000 simulated users, in-process → `sim/report.json` or over HTTP (`--url`) → `sim/report_http.json` | exists |

Run order (offline, from `mvp/offline`, venv Python 3.12): `smoke → build_data → extract → train_probe → external_eval → gen_actions → build_scenarios`. `scenario_pick.py` is shared by `gen_actions` and `build_scenarios` so both use the same 9 rows (`pick(rows, scores, threshold)`).

## Data flow — offline (laptop, CPU)
1. `build_data.py`: SQuAD validation contexts → 150 docs → per doc: 1 clean row with benign insertion + 1 row per trained style; 40 hard negatives; split by `doc_id` 70/15/15; held-out Hindi/Hinglish rows (injected + benign control) from test docs only.
2. `extract.py`: for each row, chat template `system → user(task) → assistant(fetch_page call) → tool(page)` + generation prompt; hidden state at the last token (assistant start) for layers 6/9/12/15/18; `Δ = state(task, page) − state(task, None)`.
3. `train_probe.py`: scaler + logistic regression per layer on train; best layer by val AUROC; threshold at 5 % val FPR; metrics on test + heldout; keyword baseline; shuffled-label control.
4. `gen_actions.py`: same prompt, greedy generation of `{"tool":"send_email",...}` → `action_source` = `model` if it emails the attacker, else `scripted`.
5. `build_scenarios.py`: 9 scenarios with `probe_score`, `keyword_hit`, `action_source`, steps → `api/data/`.

## Data flow — site (Vercel)
`public/app.js` → `POST /api/run {scenario_id, threshold}` → `api/index.py` loads `api/data/*.json` once at import → for each defence (`none`, `keyword`, `anchor`): read step sets score; `score ≥ threshold` → run **tainted** → later `send_email` (side effect) **blocked**; unblocked email containing `SECRET` → `leaked` → verdict `leaked` / `safe` / `false_block` → JSON → UI columns.

Leak rule: an unblocked email leaks if its body contains the secret or it goes to the scenario's attacker address. Request bodies > 2 KB (counted as bytes arrive, chunked too) → 413; repeated JSON keys or nesting too deep to parse → 422 (both in the `BodyCap` ASGI middleware); bad input → 404/422 (strict pydantic model). Vercel adds security headers from `vercel.json` (CSP with the inline theme-script hash, nosniff, no-referrer, frame DENY).

## Modules
| Module | Responsibility | Talks to |
|---|---|---|
| `mvp/offline/` | real model work, writes all numbers | HF hub (first download), local files |
| `mvp/api/index.py` | taint rule + serve JSON; no ML imports | `api/data/*.json` |
| `mvp/public/` | UI | `/api/*` |
| `mvp/tests/` | pytest on data + API | `offline/data`, `offline/out`, `api` |

## External services
- Hugging Face Hub: model + SQuAD download, offline only, first run. Llama-3.2-3B and Prompt Guard 2 are gated: token from git-ignored `mvp/offline/.env` or `v2/offline/.env` (`HF_TOKEN`); on Kaggle from Kaggle Secrets.
- Vercel: hosts `mvp/` (Root Directory = `mvp`).
- Planned: Pipelock binary (local, unmodified) in front of the live agent's outbound traffic; benign-instruction-bench + AgentDojo / τ-bench / BIPIA sources (downloaded once, offline).

## Full product (`v2/`, H0 built 2026-10-30)
`mvp/` stays frozen. `v2/` is a copy of the MVP with the model switch. Run from `v2/offline/`, in the MVP order,
each with `--model {qwen0.5b,llama3b}` (default `qwen0.5b`) and an optional `--precision` (qwen: `fp32`; llama:
`nf4` = NF4 weights + fp16 compute, or `bf16`/`fp16`/`fp32`).

| Entry point | What it does |
|---|---|
| `v2/offline/common.py` | `MODELS` table, `parse()` → `Run` (paths `data/<model>/`, `features/<model>/`, `out/<model>/`), `run_meta()`, `check_run_meta`/`load_probe` (raise `RunMismatch`), `load_env()` (HF token: `v2/offline/.env`, then `mvp/offline/.env`), `load_model(run)` → (tok, model, device), `render()` (fixed template date) |
| `v2/offline/attacks.py` | H1 attack families + Tamil: templates, encoders (base64/ROT13/hex, TAG, zero-width, Cyrillic), JSON shapes, length matching (`matched`, ±10 %) |
| `v2/offline/{smoke,build_data,extract,train_probe,external_eval,gen_actions,build_scenarios}.py` | same as the MVP steps; outputs in `out/<model>/`, each with `run_meta`; `build_scenarios` copies the given model's files into `v2/api/data/` |
| `v2/offline/check_gpu.py` | unchanged copy → `out/gpu_check.json` |
| `v2/offline/run_gpu.md` | ordered, resumable 3B commands (G1–G5), folder table, files to bring back |
| `v2/kaggle/make_notebook.py` → `anchor_3b.ipynb` | Kaggle T4: clone repo, `HF_TOKEN` from Kaggle Secrets (env only), run `run_gpu.md` steps 1–8 with `--model llama3b --precision nf4`, zip `out/llama3b/` + `data/llama3b/` + `out/gpu_check_kaggle.json` |
| `v2/anchor/policy.py` | `run_defence(scn, defence, threshold, secret)`: the taint rule, shared |
| `v2/api/index.py` | MVP replay API importing `anchor.policy`; serves the model that `build_scenarios` copied; `/api/health` adds `run_meta` |
| `v2/public/`, `v2/sim/` | MVP site and simulation copies; sim compares with `out/<served model>/` |

Data flow (offline, per model): SQuAD + templates + `attacks.py` families (appended after the v1 rows; split payloads carry `prior_outputs`) → `data/<model>/rows.jsonl` → Δ activations at two positions (`delta_L*.npy` assistant start, `delta_end_L*.npy` last tool-output token) `features/<model>/` (meta.json = run_meta) → probe (position + layer chosen on val; thresholds at 5 % and 1 % val FPR) `out/<model>/probe.json` + metrics/scores → InjecAgent external block → actions → scenarios → `v2/api/data/`.

## Planned (full product) — not built yet
Paths below written as `mvp/...` map to `v2/...`. Every script takes `--model {qwen0.5b,llama3b}` and writes `run_meta`.

| Command / route | What it will do |
|---|---|
| `mvp/offline/baselines.py` | Prompt Guard 2 22M/86M, Horizon guard, PIGuard, ProtectAI v2, Pipelock scanner, keyword list, length+position control on the same splits → `out/baselines.json` |
| `mvp/offline/agentbench.py` | rebuild AgentDojo / τ-bench / BIPIA tool-output sets (benign-instruction-bench), score frozen Anchor at 1 % FPR → `out/agentbench.json` |
| `mvp/offline/adaptive.py` | black-box rewrite attacker (CPU) and GCG suffix (GPU laptop) against the scorer → `out/adaptive.json` |
| `v2/offline/run_gpu.md` | ordered commands for the GPU laptop run; which files to bring back — **exists** with G1 + G2 estimate; H0 adds G2–G5 commands |
| `mvp/anchor/scorer.py` | load model + probe once; `score(task, outputs) → drift, attribution, run_meta`; fail closed |
| `mvp/anchor/policy.py` | steer mode (taint rule already in `v2/anchor/policy.py`) |
| `mvp/agent/` | live multi-turn loop: model picks JSON action → tool → scorer → act or taint; tools served by a local mock server; outbound via Pipelock |
| `POST /api/score` (live) | playground: text → drift score + highlighted sentences |
| `POST /api/agent/run` (live) | one live agent run, vanilla vs Anchor, with per-layer log (Anchor / Pipelock) |
| `GET /api/health` | adds `mode: live|replay` and `run_meta` |

Planned data flow (live): user task → agent loop → tool call → (Pipelock fetch proxy) → tool output → scorer Δ at assistant start with all earlier outputs → probe → taint? → next action → side effect → (Pipelock forward proxy, DLP) → mock mail.
