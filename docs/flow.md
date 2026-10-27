# Flow

Update this file whenever an entry point or data path changes. Everything is **(planned)** until built.

## Entry points
| Command | Purpose |
|---|---|
| `python code/main.py demo` | Run the poisoned-page demo: vanilla agent vs agent + Anchor |
| `python code/model/server.py` | Start FastAPI model server (`/health`, `/score`, `/steer`) |
| `python code/data/build.py` | Build clean + injected dataset with document-level split |
| `python code/probe/train.py --layer <n>` | Extract Δ activations, train probe, write `code/.cache/probe/` |
| `python code/steer/train.py` | Compute steering vector |
| `python code/evaluation/main.py --run-name <n>` | Score probe and agents → `code/evaluation/evaluation_report.md` |
| `python code/package.py` | Build zip (excludes caches, secrets, model weights) |
| `python code/model/smoke.py` | Dev: one live model call + VRAM print |

## Per-tool-output pipeline (planned)
`agent.loop` → tool returns output → `anchor.check(task, output)` → `/score` → `drift_score` →
below threshold: action proceeds · above threshold: `steer.apply` or `block` → outbound requests pass through
Pipelock → result and score logged to `code/.cache/runs/<run>/events.jsonl`.

## Scoring (planned)
`activations(task)` and `activations(task + output)` → residual stream at layer L, last token →
`Δ = act(task + output) − act(task)` → linear probe → `drift_score` → compare to threshold.

## Data path (per demo run)
1. User task + scripted tools loaded.
2. Agent turn: model picks action; tool runs; output returned.
3. Anchor check:
   1. Two forward passes (task alone, task + output), hidden states captured.
   2. Δ computed, probe scores it.
   3. Score logged with layer, probe version, threshold.
4. Decision: act · block · steer (+ re-generate the turn with the hook on).
5. Outbound call (e.g. `send_email`) → Pipelock egress proxy → mock Internet.
6. Web demo reads `events.jsonl` and draws the drift-score trace for each agent.

## Data path (training)
1. `data/build.py` → rows (`task, output, label, injection_style`) split by document and style.
2. `probe/train.py` → Δ per row → fit probe → pick threshold on validation.
3. `steer/train.py` → mean activation difference → steering vector file.
4. Artifacts saved under `code/.cache/probe/`, keyed by model, layer and data hash.
