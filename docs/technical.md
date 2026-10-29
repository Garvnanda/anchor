# Technical design (full product)

> Builds on the MVP in `mvp/` (`implementation_mvp.md`). Everything marked **exists** is shipped and tested;
> everything else is planned in `implementation.md`. **Planned code lives in a new folder (`v2/`, named at H0), not in `mvp/`** — `mvp/` is frozen as the deployed MVP. Planned paths below written as `mvp/...` map to the same place under `v2/`. Who builds what: `implementation.md` (H / G phases).

Language: Python 3.12. Model: **Llama-3.2-3B-Instruct** for every reported number; `Qwen2.5-0.5B-Instruct` as the
CPU dev model that every script is first run with. One model constant + precision setting selects them.
Libraries: `torch`, `transformers`, `scikit-learn`, `numpy`, `datasets`, `fastapi`, `pydantic`, `httpx`, `pytest`
(+ `bitsandbytes` only if the 4-bit GPU path is chosen). External, unmodified: **Pipelock** (Go binary).

## 0. Two machines, one pipeline
- **Dev laptop** (this one: Core Ultra 7 155H, 16 GB, CPU): all code is written and tested here end to end with
  the 0.5B model. The 3B model may also run here on CPU in bf16 if the speed spike is acceptable.
- **GPU laptop** (RTX 2050, 4 GB): runs scripts it is given, in the order of `mvp/offline/run_gpu.md` (planned),
  and returns the files it writes (`out/*.json`). Needed for anything with gradients on 3B (adaptive suffix
  attack, steering-vector training if heavy).
- **Rule:** the probe is trained and served with the same model build and precision. A probe trained on 4-bit
  activations is never applied to bf16 activations or the other way round.
- Every script: `--model {qwen0.5b,llama3b}`, resumable (checkpoints), writes a `run_meta` block (model, precision,
  device, versions, date) into its output so the site can show where each number came from.

## 1. Components

```
                 ┌──────────── live (laptop) ────────────┐        ┌──── deployed (Vercel) ────┐
user task ─► [A AGENT LOOP] ─► tool call ─► [P PIPELOCK fetch / forward proxy] ─► web / mock mail
                  ▲                              │ tool output
                  │ act                          ▼
                  │                      [B ANCHOR SCORER]  Llama-3.2-3B hidden states
                  │                       Δ at assistant start → linear probe → drift score
                  └── drift low ◄────────────────┤
                      drift high ─► run tainted ─► [C BLOCK / STEER] later side effects
[D PLAYGROUND]  paste any text → live score + which sentences pushed it
[E OFFLINE PIPELINE]  data · attacks · activations · probe · baselines · agent-bench · adaptive attacks
[F SITE]  same frontend: live mode (laptop) or replay mode (Vercel, measured 3B results)
```

### 1.1 Offline pipeline (`mvp/offline/`) — exists for 0.5B, extended
- **exists:** `build_data` (document split, 5 trained styles, held-out Hindi with benign controls, hard negatives,
  JSON tool responses), `extract` (chat template, tool role, Δ at assistant start, layers sweep, feature cache),
  `train_probe` (val layer + threshold, shuffled control, keyword baseline), `external_eval` (InjecAgent),
  `gen_actions`, `build_scenarios`.
- **changes:** model/precision switch; layers swept for 3B (28 layers); thresholds reported at **1 % and 5 %**
  validation FPR; metrics carry `run_meta`; the keyword baseline is replaced on the site by real baselines (1.4).
- **new control:** a length + position-only classifier on the same splits (arXiv 2610.18408). If it gets close to
  the probe, the probe result is not reported as intent detection.

### 1.2 Attack families (`mvp/offline/attacks.py`, planned)
Each family is a generator that turns a clean tool output into an injected one, with the same document split and
train/val/test template split as today. Families are tagged **trained** or **held out** (never trained or tuned on).

| Family | Example | Notes |
|---|---|---|
| html_comment, visible_imperative, markdown_hidden, polite_no_triggers, user_voice, json_tool | exists | MVP styles |
| encoded | base64 / hex payload with a decode hint; leetspeak | Pipelock normalises some of these |
| invisible_unicode | instruction in Unicode TAG chars (U+E0000–E007F), zero-width joins, bidi overrides | renders as nothing, tokenizer still sees it |
| homoglyph | Cyrillic/Greek look-alikes in trigger words | beats keyword lists |
| split_payload | first half in tool output 1, second half in tool output 2 | needs multi-output scoring (1.3) |
| tool_description | poisoned MCP `tools/list` description | scored as a tool output |
| rag_document | instruction inside a retrieved knowledge-base chunk among clean chunks | multi-chunk tool output |
| multilingual | Hindi/Hinglish (held out, exists) + Tamil (held out, Tamil script) with benign-Tamil controls | transfer test across scripts |
| exfil_link | markdown image / link whose URL carries the secret | Pipelock's job; shows the layering |

### 1.3 Anchor scorer (`mvp/anchor/scorer.py`, planned; logic from `extract.py`)
- Input: task, tool name, tool output (and, for split payloads, the run's earlier tool outputs).
- Δ = state(task + outputs so far) − state(task + outputs before this one), read at the assistant-start token,
  probe layer from the sweep. Cached task-only state per task.
- Output: `drift_score` ∈ [0, 1], `layer`, `probe_version`, `run_meta`, latency.
- **Attribution** for the playground: which sentences pushed the score. Method decided in its phase by comparing
  a cheap one-pass method (projection of per-token states onto the probe direction) against leave-one-sentence-out
  re-scoring offline; the cheap one ships only if it agrees.
- Fail closed: scorer error or timeout → the pending side effect is blocked and the reason shown.

### 1.4 Baselines (`mvp/offline/baselines.py`, planned)
All run on the same rows, thresholds set on the same validation split at the same FPR targets.

| Baseline | Kind | Licence / access |
|---|---|---|
| Prompt Guard 2 22M and 86M (Meta) | text classifier | Llama licence, gated (user's HF token) |
| Horizon-Labs prompt-injection-guard-base | text classifier, top of the 2026 agent-benchmark table | check model card (pin revision; weights changed 2026-10-02) |
| PIGuard | text classifier | check model card |
| ProtectAI deberta-v3-base-prompt-injection-v2 | text classifier | Apache-2.0 |
| Pipelock response scanner (34 patterns + 6-pass normalisation) | rules | Apache-2.0, run unmodified |
| Keyword list (MVP) | rules | ours; kept only as the simplest reference |
| Length + position only | control | ours |

### 1.5 Agent-benchmark evaluation (`mvp/offline/agentbench.py`, planned)
- Rebuild the AgentDojo, τ-bench and BIPIA tool-output sets with the scripts of `lzwhehe/benign-instruction-bench`
  (MIT; benign outputs by replaying ground-truth tool calls, injected outputs by differential replay; CPU only).
- Score Anchor-3B on them with **its own probe frozen** (never trained or tuned on these sets); threshold set at
  1 % FPR on each benchmark's benign outputs, exactly as the paper does, so our row is comparable with their table.
- Report next to their published numbers, labelled as theirs; re-run 2–3 baselines ourselves to check we
  reproduce their setup.

### 1.6 Block or steer (`mvp/anchor/policy.py`, planned; logic exists in `api/index.py`)
- **Taint rule (exists):** score ≥ threshold on any tool output → run tainted → every later side-effecting action
  blocked; read-only actions continue.
- **Steer (stretch):** forward hook adds a vector at the probe layer on tainted runs; vector = mean difference of
  task-following vs drifted states; strength tuned on validation. Counts only if attack success drops and the
  user's task still completes. Mode `ANCHOR_MODE=block|steer|both`, default `block`.

### 1.7 Live agent loop (`mvp/agent/`, planned; prompt + parser from `gen_actions.py`)
- Tools: `fetch_page`, `read_file`, `search_kb` (RAG chunks), `list_tools` (MCP-style descriptions) — read-only;
  `send_email` — side effect. All local: pages and mailbox are served by a local mock server.
- Each turn: model chooses an action (JSON) → tool runs → output → Anchor scorer → act, or taint and block later
  side effects. Turn cap; same loop for vanilla and Anchor variants.
- Outbound traffic goes through **Pipelock** (fetch proxy for pages, forward proxy for `send_email`'s HTTP call),
  so its DLP can stop a secret leaving even if Anchor misses. Logs record which layer stopped what.

### 1.8 Adaptive attacks (`mvp/offline/adaptive.py`, planned)
- **Black-box (CPU):** an attacker loop rewrites a failed injection (paraphrase, change voice, move position,
  encode) using the scorer's yes/no output; report attack success vs number of queries.
- **White-box (GPU laptop):** multi-probe GCG suffix as in arXiv 2602.00750; report evasion rate, then the
  suffix-augmentation defence if time allows.

### 1.9 Live server and site
- **Live server (laptop):** FastAPI, same hardened app as the MVP (body cap, strict models, headers) plus
  `/api/score` (playground), `/api/agent/run` (live loop). Sync handlers + one model lock; requests queue.
  `/api/health` reports `mode: live|replay` and `run_meta`. Rate limit and input length cap on `/api/score`.
- **Deployed (Vercel):** replay of measured 3B results (scenarios, grid, baselines, agent-bench table).
- **Optional bridge:** deployed site calls the laptop through a tunnel when it is up, falls back to replay;
  adds attack surface → built last, behind a security pass.
- **Frontend:** redesigned after features are fixed, using the `hallmark` skill; less text, visual story
  (run trace, drift gauge, highlighted sentences, attack grid).

## 2. Messy-input behaviour
| Situation | Behaviour |
|---|---|
| Tool output longer than the scoring budget | Score the first N tokens and the last N tokens separately, take the max; flag truncation. |
| Tool output empty | Score skipped; treated as clean; logged. |
| Invisible / encoded characters | Scored as the model receives them (no stripping); shown escaped in the UI. |
| Injection in a language other than English | Scored like any output; per-language results reported. |
| Attack split across tool outputs | Δ uses all earlier outputs (1.3), so the second half is scored in context. |
| Score near the threshold | Flagged `borderline`; block mode blocks. |
| Scorer down, OOM or timeout | Fail closed: side effect blocked, reason shown. |
| Pipelock unreachable | Outbound requests refused (fail closed). |
| Output tries to instruct the checker | Treated as data; scoring uses activations, not model replies. |

## 3. Open questions (resolve during build, record in `decisions.md`)
- Which machine and precision runs 3B (CPU bf16 here vs 4-bit on the RTX 2050) — after the speed spike.
- 3B probe layer; whether 1 % FPR is reachable on our validation data.
- Attribution method for the playground (1.3).
- Does 3B get hijacked by our pages often enough for model-sourced leaks, or do we need stronger pages?
- Steering: worth it in the time left?
