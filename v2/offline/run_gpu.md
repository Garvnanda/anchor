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
