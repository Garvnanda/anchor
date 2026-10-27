# Technical design

Language: Python. Entry point: `python code/main.py` (planned). Model: Llama-3.2-3B-Instruct, 4-bit.
Libraries (planned): `transformers`, `bitsandbytes`, `torch`, `scikit-learn`, `fastapi`, `pydantic`, `pytest`.
Unmodified external component: **Pipelock** egress proxy.

## 1. Components

```
user task ─► [1 AGENT LOOP] ─► tool call ─► tool output (web page / file)
                  ▲                              │
                  │ act                          ▼
                  │                      [2 ANCHOR  /score]
                  │                       model + hidden states
                  │                       drift probe → score
                  │                              │
                  └── drift low ◄────────────────┤
                      drift high ─► run tainted ─► [3 BLOCK / STEER] side-effecting actions
[4 PIPELOCK egress proxy]  Layer 2 (network) ─► Internet
[5 WEB DEMO]  [6 EVAL]
```

### 1.1 Model server (`code/model/`)
- Load Llama-3.2-3B-Instruct in 4-bit; `output_hidden_states=True`.
- FastAPI app; endpoints `/health`, `/score`, `/steer`, `/demo`.
- Handlers are sync `def` (FastAPI runs them in its threadpool) plus one GPU lock around every model call; requests queue on the lock. No auto-reload.
- Model fails to load → mock mode, announced loudly: startup log banner, `mode: "mock"` in `/health` and `/score`, badge in the UI.
- `ANCHOR_REQUIRE_LIVE=1` → server refuses to start instead of falling back to mock.

### 1.2 Drift probe (`code/probe/`)
- Δ = act(task + output) − act(task), from the residual stream at one middle layer (layer chosen in Phase 2, recorded in `decisions.md`).
- Input format: Llama chat template, user turn = task, tool turn = output.
- Token position: assistant-turn start token. Last token of raw output stays a Phase 2 comparison only.
- Probe: linear classifier (logistic regression) on Δ, trained on clean vs. injected tool outputs. CPU, seconds.
- Output: `drift_score` in [0, 1] + the layer / probe version used.
- Threshold chosen on a held-out split, never on the demo page.
- The L2 norm of Δ through a fixed sigmoid (removed scaffold) is a **placeholder** to be replaced by the probe, not tuned.

### 1.3 Block or steer (`code/steer/`)
- **Taint model**: the score is attached to the tool output, not to the action. Score ≥ threshold → the run is tainted. Once tainted, every later side-effecting action (`send_email`, outbound requests) is blocked, even if that action's own text looks clean. Read-only actions (`fetch_page`, `read_file`) may continue.
- On a tainted run, one of:
  - **Block**: the pending side-effecting action is refused; agent gets a fixed refusal message.
  - **Steer**: forward hook adds a steering vector at the chosen layer that pulls the model back to the task.
- Steering vector: mean activation difference, task-following vs. drifted, trained on CPU. Strength is a parameter; tuned in Phase 3.
- Mode (`block` / `steer` / `both`) set by config (`ANCHOR_MODE`, not wired up yet).

### 1.4 Agent loop (`code/agent/`)
- Tools: `fetch_page`, `read_file` (read-only), `send_email` (side-effecting). All local/mock; no real internet or mail in the demo.
- Each turn: action → tool → tool output → **Anchor check** → act, or taint run and block/steer later side effects.
- Max turns configurable; same loop for the vanilla and the Anchor agent so the comparison is fair.
- Two modes:
  - **Scripted** (removed scaffold; for UI testing only): actions fixed in code.
  - **Model-driven**: after reading the page the model generates the next action (constrained choice of tool + args). The demo uses this mode; cached runs as fallback.

### 1.5 Egress layer
- Pipelock, unmodified, in front of outbound requests (HTTP, WebSocket, MCP). Second line of defence for secret exfiltration.
- Anchor never edits Pipelock; integration is routing only.

### 1.6 Data (`code/data/`)
- Clean tool outputs: ordinary pages and files.
- Injected tool outputs: same documents with injection text (HTML comment, visible text, markdown, split across paragraphs, other languages).
- Split by **document** and by **injection style** (not by random row) so the probe is tested on unseen styles.
- Every row: `id, task, output, label, injection_style, source`.

### 1.7 Evaluation (`code/evaluation/`)
- Metrics: detection rate (TPR) at fixed FPR, false-block rate on clean outputs, attack success rate with / without Anchor, added latency per tool output, VRAM.
- Baselines: no defence; keyword filter.
- Writes `code/evaluation/evaluation_report.md`.

## 2. Messy-input behaviour
| Situation | Behaviour |
|---|---|
| Tool output very long | Truncate to the model context limit; flag truncation; score the kept part. |
| Tool output empty | Score skipped; treated as clean; logged. |
| Injection in a language other than English | Scored like any output; per-language results reported. |
| Score within a margin of the threshold | Flagged `borderline`; block mode blocks, steer mode steers. |
| Attack split across several tool outputs | Each scored alone; known limitation unless the multi-output case is added in Phase 6. |
| Model server down or OOM | Fail closed: action blocked, error logged. |
| Model fails to load | Mock shown in UI and logs; `ANCHOR_REQUIRE_LIVE=1` refuses to start. |
| Output tries to instruct the checker | Treated as data; scoring uses activations, not model replies. |
| Pipelock unreachable | Outbound requests refused (fail closed). |

## 3. Open questions (resolve during build, record in `decisions.md`)
- Which middle layer gives the best probe (read position decided: assistant-turn start).
- Block vs. steer vs. both as the default.
- Threshold and FPR target.
- Real VRAM and latency on the RTX 2050.
- How well a probe trained on our injection styles transfers to unseen styles.
- Does 3B get hijacked reliably by our poisoned page? If not, how often, and which page variant?
