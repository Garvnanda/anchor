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
                      drift high ─► [3 BLOCK / STEER]
[4 PIPELOCK egress proxy]  Layer 2 (network) ─► Internet
[5 WEB DEMO]  [6 EVAL]
```

### 1.1 Model server (`code/model/`)
- Load Llama-3.2-3B-Instruct in 4-bit; `output_hidden_states=True`.
- FastAPI app; one endpoint family: `/score`, `/steer`, `/health`.
- One model instance, one lock (single GPU); requests queue.

### 1.2 Drift probe (`code/probe/`)
- Δ = act(task + output) − act(task), from the residual stream at one middle layer (layer chosen in Phase 2, recorded in `decisions.md`).
- Token position: last token (alternatives compared in Phase 2).
- Probe: linear classifier (logistic regression) on Δ, trained on clean vs. injected tool outputs. CPU, seconds.
- Output: `drift_score` in [0, 1] + the layer / probe version used.
- Threshold chosen on a held-out split, never on the demo page.

### 1.3 Block or steer (`code/steer/`)
- Score ≥ threshold → one of:
  - **Block**: the pending action (tool call / email) is refused; agent gets a fixed refusal message.
  - **Steer**: forward hook adds a steering vector at the chosen layer that pulls the model back to the task.
- Steering vector: mean activation difference, task-following vs. drifted, trained on CPU. Strength is a parameter; tuned in Phase 3.
- Mode (`block` / `steer` / `both`) set by config.

### 1.4 Agent loop (`code/agent/`)
- Scripted tools: `fetch_page`, `read_file`, `send_email`. All local/mock; no real internet or mail in the demo.
- Each turn: model action → tool → tool output → **Anchor check** → act or block/steer.
- Max turns configurable; same loop for the vanilla and the Anchor agent so the comparison is fair.

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
| Output tries to instruct the checker | Treated as data; scoring uses activations, not model replies. |
| Pipelock unreachable | Outbound requests refused (fail closed). |

## 3. Open questions (resolve during build, record in `decisions.md`)
- Which middle layer and token position give the best probe.
- Block vs. steer vs. both as the default.
- Threshold and FPR target.
- Real VRAM and latency on the RTX 2050.
- How well a probe trained on our injection styles transfers to unseen styles.
