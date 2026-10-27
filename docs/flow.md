# Code flow
Update whenever an entry point or data path changes. MVP layout from `implementation_mvp.md` §2. Nothing exists yet; every row is **planned**.

## Entry points
| Command / route | What starts here | Status |
|---|---|---|
| `mvp/offline/build_data.py` | SQuAD docs + injections + hard negatives → `offline/data/rows.jsonl`, `out/data_summary.json` | planned |
| `mvp/offline/extract.py` | rows → Δ activations per layer → `offline/features/delta_L{n}.npy` | planned |
| `mvp/offline/train_probe.py` | probe per layer, threshold, keyword baseline, shuffled control → `out/probe.json`, `metrics.json`, `layer_sweep.json` | planned |
| `mvp/offline/gen_actions.py` | model picks next action per demo scenario → `out/actions.json` | planned |
| `mvp/offline/build_scenarios.py` | 8 test/heldout scenarios + scores → `out/scenarios.json`; copies JSON into `api/data/` | planned |
| `GET /api/health` | mode, model, layer, threshold, built_at | planned |
| `GET /api/scenarios` | scenario list | planned |
| `POST /api/run` | three defence traces for one scenario + threshold | planned |
| `GET /api/metrics` | metrics + layer sweep | planned |
| `mvp/public/index.html` | site UI, calls `/api/*` | planned |
| `mvp/sim/` | Phase 4.5 simulated users against the local API | planned |

## Data flow — offline (laptop, CPU)
1. `build_data.py`: SQuAD validation contexts → 150 docs → per doc: 1 clean row with benign insertion + 1 row per trained style; 40 hard negatives; split by `doc_id` 70/15/15; held-out Hindi/Hinglish rows (injected + benign control) from test docs only.
2. `extract.py`: for each row, chat template `system → user(task) → assistant(fetch_page call) → tool(page)` + generation prompt; hidden state at the last token (assistant start) for layers 6/9/12/15/18; `Δ = state(task, page) − state(task, None)`.
3. `train_probe.py`: scaler + logistic regression per layer on train; best layer by val AUROC; threshold at 5 % val FPR; metrics on test + heldout; keyword baseline; shuffled-label control.
4. `gen_actions.py`: same prompt, greedy generation of `{"tool":"send_email",...}` → `action_source` = `model` if it emails the attacker, else `scripted`.
5. `build_scenarios.py`: 8 scenarios with `probe_score`, `keyword_hit`, `action_source`, steps → `api/data/`.

## Data flow — site (Vercel)
`public/app.js` → `POST /api/run {scenario_id, threshold}` → `api/index.py` loads `api/data/*.json` once at import → for each defence (`none`, `keyword`, `anchor`): read step sets score; `score ≥ threshold` → run **tainted** → later `send_email` (side effect) **blocked**; unblocked email containing `SECRET` → `leaked` → verdict `leaked` / `safe` / `false_block` → JSON → UI columns.

## Modules
| Module | Responsibility | Talks to |
|---|---|---|
| `mvp/offline/` | real model work, writes all numbers | HF hub (first download), local files |
| `mvp/api/index.py` | taint rule + serve JSON; no ML imports | `api/data/*.json` |
| `mvp/public/` | UI | `/api/*` |
| `mvp/tests/` | pytest on data + API | `offline/data`, `offline/out`, `api` |

## External services
- Hugging Face Hub: model + SQuAD download, offline only, first run.
- Vercel: hosts `mvp/` (Root Directory = `mvp`).
