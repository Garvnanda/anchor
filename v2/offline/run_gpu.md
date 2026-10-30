# GPU runs (Garv, RTX 2050 4 GB) — ordered, resumable

All 3B numbers come from this laptop at the G1 precision. Commit only `out/*.json`; never `.npy`, weights or `.env`.

## Setup (once)
```
cd v2/offline
uv venv --python 3.12 .venv
uv pip install --python .venv/Scripts/python.exe -r requirements-gpu.txt
```
`HF_TOKEN` (Llama-3.2 access) in `v2/offline/.env` (git-ignored). First model download ~6 GB to `~/.cache/huggingface`.

## G1 — GPU check + 3B smoke (done 2026-10-30)
| Step | Command | Runtime | Bring back |
|---|---|---|---|
| 1 | `.venv/Scripts/python check_gpu.py` | ~15 s | `out/gpu_check.json` |
| 2 | `.venv/Scripts/python smoke_llama3b.py` | ~11 min first run (download), ~1 min after | `out/smoke_llama3b.json` |

Precision (fixed, `decisions.md` 2026-10-30): Llama-3.2-3B-Instruct, bitsandbytes NF4 weights, bf16 compute,
no double quant, `date_string="26 Jul 2024"` in the chat template.

Measured (`out/smoke_llama3b.json`): 0.8305 s per pass on a 400-token page (515 prompt tokens),
0.2273 s for the task-only pass; peak reserved 2.94 GB of 4.29 GB (1.354 GB headroom); repeat passes bit-identical.

## G2 — 3B activations + probe (estimate)
Extraction = one pass per row (+ one task-only pass per distinct task, negligible). At 0.8305 s per worst-case
(400-token) pass: **~14 min per 1,000 rows**; MVP dataset size (1,434 rows) ≈ 20 min; ~1 min model load.
Pages shorter than 400 tokens run faster, so this is an upper bound. Commands are added by H0/H1 once the v2
pipeline (`--model llama3b`) exists.
# 3B runs on the GPU laptop (Garv)

Ordered, resumable commands for every Llama-3.2-3B step. Run from `v2/offline/`. Each step writes only under
`out/llama3b/`, `data/llama3b/` or `features/llama3b/`, so it never touches Haragam's 0.5B files in
`out/qwen0.5b/`.

## Where files go (both laptops)

| Folder | What | Commit? |
|---|---|---|
| `data/<model>/rows.jsonl` | dataset; the token budget is checked with that model's tokenizer | **yes** |
| `features/<model>/` | Δ activations (`cache.npz`, `delta_L*.npy`, `meta.json`) | **no** (git-ignored, large) |
| `out/<model>/*.json` | probe, metrics, scores, actions, scenarios; every file has `run_meta` | **yes** |
| `out/gpu_check.json` | `check_gpu.py` result (machine, not model) | **yes** |
| `data/external/` | InjecAgent copy, re-downloaded by `external_eval.py` | no |

`<model>` is `qwen0.5b` (Haragam, CPU) or `llama3b` (Garv, GPU). Pick the model with `--model`; the default is
`qwen0.5b`, so **every 3B command below passes `--model llama3b`**.

## One-time setup
```
git pull
python -m venv .venv && .venv\Scripts\activate          # Windows; Linux: source .venv/bin/activate
pip install torch --index-url https://download.pytorch.org/whl/cu128
pip install -r requirements.txt bitsandbytes             # requirements.txt pins the CPU torch; the line above wins
```
- HF token with Llama-3.2 access: one line `HF_TOKEN=hf_...` in `v2/offline/.env`. The file is git-ignored.
  Never commit it or paste it into chat.
- Close other GPU/RAM users (browsers, games, RGB tools) before long runs.

## Precision (one 3B setup)
Default `--precision nf4` = 4-bit NF4 weights with **fp16** compute, the same on Garv's RTX 2050 and on the Kaggle T4
(`kaggle/anchor_3b.ipynb`, which runs these same steps). G1 confirms it. If G1 picks another value, pass the
same `--precision` to **every** command. Scripts refuse to mix precisions: `extract.py` stops when `features/llama3b/`
holds another precision (delete that folder to start over), and `external_eval` / `gen_actions` refuse a `probe.json`
with a different `run_meta`.

## Steps

| # | Phase | Command | Writes | Expected time |
|---|---|---|---|---|
| 1 | G1 | `python check_gpu.py` | `out/gpu_check.json` | < 1 min |
| 2 | G1 | `python smoke.py --model llama3b` | `out/llama3b/smoke.json` (hidden states 29, pass time) | ~2 min + first download (~6.5 GB) |
| 3 | G2 | `python build_data.py --model llama3b` | `data/llama3b/rows.jsonl`, `out/llama3b/data_summary.json` | ~1 min |
| 4 | G2 | `python extract.py --model llama3b` | `features/llama3b/` (checkpoint every 100 rows) | rows × 2 passes × smoke pass time (fill in at G1) |
| 5 | G2 | `python train_probe.py --model llama3b` | `out/llama3b/probe.json`, `metrics.json`, `layer_sweep.json`, `scores.json` | ~2 min (CPU) |
| 6 | G2 | `python external_eval.py --model llama3b` | `external` block in `metrics.json`, `out/llama3b/external_scores.json` | ~400 rows × 2 passes |
| 7 | G4 | `python gen_actions.py --model llama3b` | `out/llama3b/actions.json` (9 generations) | ~5 min |
| 8 | G4 | `python build_scenarios.py --model llama3b` | `out/llama3b/scenarios.json`, `probe_meta.json`; also overwrites `v2/api/data/` (**do not commit `api/data/`**: which model the site serves is decided in H7/H8) | seconds |
| 9 | G3 | `python agentbench.py --model llama3b` (written in H3) | `out/llama3b/agentbench.json` | — |
| 10 | G5 | `python adaptive.py --model llama3b` (written in H6) | `out/llama3b/adaptive.json` | — |

**Resuming:** step 4 caches by row content. If it stops (crash, sleep, closed lid), run the same command again
and it continues from the last checkpoint. When H1 changes the dataset, rerun steps 3–6; only new or changed rows
are extracted.

**Order rules:** run 5 after 4; run 6, 7 and 8 after 5 (each re-checks the probe's `run_meta`). Step 5 rewrites
`metrics.json`, so after it always rerun 6 and then 8.

## Bring back (commit and push yourself)
```
git add v2/offline/out/gpu_check.json v2/offline/out/llama3b/ v2/offline/data/llama3b/
git commit -m "G2: llama3b probe run"     # never --no-verify; never add .env or features/
```
Before committing, `git status` must not list `.env`, `features/`, `*.npy` or weights.

## Checks Haragam's tests run on these files
`tests/test_pipeline.py::test_every_committed_model_run_is_consistent` runs on every `out/<model>/` that has a
`metrics.json`, so once `out/llama3b/` is committed it is checked too:
- every file has `run_meta.model` equal to its folder and one precision across the folder (and the features');
- the probe's layer is the best on val; the threshold has val FPR ≤ target;
- the shuffled-label AUROC is in [0.4, 0.6]; scores cover every row of `data/<model>/rows.jsonl`.
More G2 checks (1 % FPR, position comparison, per-family TPR) are added with H1.
