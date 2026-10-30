# Anchor
Task-drift firewall for AI agents: reads an open-weight model's activations to catch prompt injection in tool outputs, then taints the run and blocks later side effects. MVP shipped (`mvp/`, frozen, https://anchor-nu-three.vercel.app). Current target: full product in `v2/` (Llama-3.2-3B, H/G phases).

## Stack
- Offline pipeline (laptop, CPU): Python, `torch` (cpu), `transformers`, `datasets`, `scikit-learn`, `numpy`; model `Qwen/Qwen2.5-0.5B-Instruct`.
- Site: FastAPI on Vercel (`mvp/api/index.py`, no ML deps) + vanilla HTML/JS in `mvp/public/`.
- Post-MVP: Llama-3.2-3B-Instruct 4-bit on RTX 2050, steering, Pipelock.

## Commands
- Offline (venv `mvp/offline/.venv`, in this order): `build_data → extract → train_probe → external_eval → gen_actions → build_scenarios` (`train_probe` rewrites `metrics.json`; `external_eval` and `build_scenarios` add their blocks after it)
- API locally: `cd mvp && uvicorn api.index:app` → `/api/health`
- v2 (from `v2/offline`, venv `../../mvp/offline/.venv`): same order with `--model {qwen0.5b,llama3b}`; outputs in `out/<model>/`
- Test: see `.claude/test-command` (mvp/tests then v2/tests)

## Docs (read on demand)
- docs/STATUS.md — resume point: read first
- docs/implementation.md — **active plan**: full-product H/G phases + gates (hooks track this file)
- docs/implementation_mvp.md — MVP phases (done; Phase 5 manual items left)
- v2/offline/run_gpu.md — 3B commands for Garv / Kaggle, per-model folder layout
- docs/idea.md — problem, approach, goals, anti-goals
- docs/technical.md — full-product design (MVP overrides noted at top)
- docs/decisions.md — why things are the way they are
- docs/flow.md — entry points and data flow
- docs/testing.md — automated + manual testing
- docs/QUESTIONS.md — open questions for the user
- docs/security/backlog.md — medium/low security findings

## Project rules
- Every number on the site comes from a file the offline pipeline wrote. No hand-typed scores.
- Keyword filter is a labelled baseline column, never shown as Anchor.
- Site copy is factual (`REPLAY`, `scripted` badges); no apologetic "fake / honesty" wording.
- Model weights, `.npy`/`.npz` features, `.env` never committed. `mvp/api/data/*.json`, `v2/api/data/*.json`, `v2/offline/out/<model>/*.json` always committed.
- `mvp/` is frozen: never edit it; new work goes in `v2/`.
- Git override (user, 2026-10-28): no `/quiz` here — stage + commit after each passed phase. Never push, never `--no-verify`.
- Planned stop after Phase 2 for the user's manual review; otherwise build straight through to deploy-ready.
- Offline venv uses Python 3.12 (`py -3.12 -m venv .venv`).
