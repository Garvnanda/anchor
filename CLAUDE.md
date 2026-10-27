# Anchor
Task-drift firewall for AI agents: reads an open-weight model's activations to catch prompt injection in tool outputs, then taints the run and blocks later side effects. Current target: same-day MVP (replay site on Vercel, real activations computed offline on CPU).

## Stack
- Offline pipeline (laptop, CPU): Python, `torch` (cpu), `transformers`, `datasets`, `scikit-learn`, `numpy`; model `Qwen/Qwen2.5-0.5B-Instruct`.
- Site: FastAPI on Vercel (`mvp/api/index.py`, no ML deps) + vanilla HTML/JS in `mvp/public/`.
- Post-MVP: Llama-3.2-3B-Instruct 4-bit on RTX 2050, steering, Pipelock.

## Commands
- Offline: `cd mvp/offline && python build_data.py && python extract.py && python train_probe.py && python gen_actions.py && python build_scenarios.py`
- API locally: `cd mvp && uvicorn api.index:app` → `/api/health`
- Test: see `.claude/test-command`

## Docs (read on demand)
- docs/STATUS.md — resume point: read first
- docs/implementation_mvp.md — **active plan**: MVP phases + gates (hooks track this file)
- docs/implementation.md — post-MVP roadmap (not tracked by hooks)
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
- Model weights, `.npy` features, `.env` never committed. `mvp/api/data/*.json` always committed.
