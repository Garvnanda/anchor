# Flow

Update this file whenever an entry point or data path changes.

> 2026-10-28: all code deleted for the MVP rebuild. "Rebuild" = existed in the removed scaffold, first to come back.

## Entry points
| Command | Purpose | Status |
|---|---|---|
| `python code/main.py demo` | Run the poisoned-page demo: vanilla agent vs agent + Anchor | rebuild (existed) |
| `python code/main.py server` | Start the server via the main entry point | rebuild (existed) |
| `python code/model/server.py` | Start FastAPI model server (`/health`, `/score`, `/steer`, `/demo`) | rebuild (existed) |
| `GET /demo` (server endpoint) | Run both agents, return JSON; the web UI calls it | rebuild (existed) |
| `python code/model/smoke.py` | Dev: one live model call + VRAM print | rebuild (existed) |
| `python code/data/build.py` | Build clean + injected dataset with document-level split | planned |
| `python code/probe/train.py --layer <n>` | Extract Δ activations, train probe, write `code/.cache/probe/` | planned |
| `python code/steer/train.py` | Compute steering vector | planned |
| `python code/evaluation/main.py --run-name <n>` | Score probe and agents → `code/evaluation/evaluation_report.md` | planned |
| `python code/package.py` | Build zip (excludes caches, secrets, model weights) | planned |

## Per-tool-output pipeline
`agent.loop` → tool returns output → `anchor.check(task, output)` → `/score` → `drift_score` →
`drift_score ≥ threshold` → mark run **tainted** → later side-effect actions (`send_email`, outbound requests) blocked
(or `steer.apply`); read-only actions may continue · below threshold and run untainted: action proceeds →
outbound requests pass through Pipelock → result and score logged.

Logging: `code/.cache/runs/<run>/events.jsonl` is **planned**. The scaffold's web demo read the `/demo` JSON response instead.

## Scoring
Chat template (user = task, tool = output) → `activations(task)` and `activations(task + output)` → residual stream
at layer L, **assistant-turn start token** → `Δ = act(task + output) − act(task)` → linear probe → `drift_score` →
compare to threshold.

## Data path (per demo run)
1. User task + tools loaded.
2. Agent turn: model picks action (model-driven mode); tool runs; output returned.
3. Anchor check on each tool output:
   1. Two forward passes (task alone, task + output) with the chat template, hidden states captured.
   2. Δ computed, probe scores it.
   3. Score logged with layer, probe version, threshold.
4. Score ≥ threshold → run tainted.
5. Decision for each later action: read-only → act · side-effecting on tainted run → block · steer (+ re-generate the turn with the hook on).
6. Outbound call (e.g. `send_email`) → Pipelock egress proxy → mock Internet.
7. Web demo draws the drift-score trace for each agent (from `/demo` JSON now; `events.jsonl` planned).

## Data path (training)
1. `data/build.py` → rows (`task, output, label, injection_style`) split by document and style.
2. `probe/train.py` → Δ per row → fit probe → pick threshold on validation.
3. `steer/train.py` → mean activation difference → steering vector file.
4. Artifacts saved under `code/.cache/probe/`, keyed by model, layer and data hash.
