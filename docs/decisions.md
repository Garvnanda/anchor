# Decisions
Append-only log at the bottom (newest last). The topic headings below are the open measured choices; each
gets date, choice, evidence once decided.

## Open choices (filled from measurements)

### Layer
- Date:
- Choice:
- Evidence: (Phase 2, `out/layer_sweep.json`, val AUROC over layers 6/9/12/15/18)

### Token position
- Date: 2026-10-28
- Choice: last token of the prompt after `add_generation_prompt=True` = assistant-turn start.
- Evidence: design (reads the state the model is about to act from). Last-token-of-raw-output is a comparison only.

### Threshold
- Date:
- Choice:
- Evidence: (Phase 2, threshold at 5 % FPR on val)

### Mode
- Date: 2026-10-28
- Choice: MVP = block only (taint → block side effects). Steer is post-MVP.
- Evidence: steering needs a live model; the MVP site is replay-only.

### Taint rule
- Date: 2026-10-28
- Choice: score attaches to the tool output; score ≥ threshold taints the run; every later side-effecting action blocked; read-only continue. Implemented exactly as `implementation_mvp.md` §4.
- Evidence: the scaffold scored the email text and could leak when the email looked clean.

### Read position
- Date: 2026-10-28
- Choice: page enters via the model's native `tool` role (after an assistant `fetch_page` call), not as a user message.
- Evidence: a user-message page reads as a user instruction, which blurs drift with ordinary instruction-following; tool role matches a real agent and the "injection via tool output" claim.

## Log

## 2026-10-28 — MVP plan is the active plan
- **Context**: two plans (`implementation.md` full product, `implementation_mvp.md` same-day MVP).
- **Decision**: workflow hooks track `docs/implementation_mvp.md`; `implementation.md` becomes the post-MVP roadmap.
- **Why**: MVP is what ships today; hooks can follow one file.
- **Alternatives**: merge into one file — rejected by user (separate file).

## 2026-10-28 — MVP model: Qwen2.5-0.5B-Instruct on CPU, fp32
- **Context**: no GPU, no HF token on the MVP machine.
- **Decision**: `Qwen/Qwen2.5-0.5B-Instruct` (Apache-2.0, not gated); final product stays Llama-3.2-3B 4-bit.
- **Why**: runs on CPU in ~2 GB; pipeline is model-agnostic (one constant).
- **Alternatives**: Llama-3.2-3B on CPU — too slow and gated.

## 2026-10-28 — Replay site on Vercel, no ML in the API
- **Context**: Vercel can't host a model.
- **Decision**: offline pipeline writes JSON; Vercel FastAPI reads it and applies the taint rule. No live `/api/score` in the MVP.
- **Why**: deployable today; live proxy adds outbound attack surface for no demo value.
- **Alternatives**: tunnel to laptop (`ANCHOR_LIVE_URL`) — post-MVP.

## 2026-10-28 — Model-chosen email action required
- **Context**: `idea.md` goal: hijack must come from the model reading the page.
- **Decision**: `gen_actions.py` always runs; trace shows `model` when the model emailed the attacker, else the scripted action with a `scripted` badge; hijack count reported.
- **Why**: real hijack where it happens; no scripted action shown as a model's.
- **Alternatives**: optional (as first drafted) — rejected.

## 2026-10-28 — Neutral site copy
- **Context**: user asked for no "fake" / "honesty" wording on the site.
- **Decision**: "Honesty footer" → "Methodology footer"; factual labels (`REPLAY`, `scripted`) stay.
- **Why**: labels are required by the scope rule; apologetic wording is not.

## 2026-10-28 — Light user simulation before deploy
- **Context**: global rule requires a ≥ 1,000-user simulation before release.
- **Decision**: Phase 4.5: 1,000 seeded simulated sessions against the local replay API + security-breaker.
- **Why**: API is cheap to hit (no model); satisfies the rule within the same-day budget.
- **Alternatives**: defer to post-MVP; full user-sim skill — slower.

## 2026-10-28 — Dataset tasks: no Hindi task
- **Decision**: replace "translate the first paragraph to Hindi" with "list the people mentioned".
- **Why**: a Hindi-related task would confound the held-out Hindi/Hinglish transfer test.

## 2026-10-28 — Frontend styles from removed scaffold
- **Decision**: recover only `web/style.css` from commit `4a4ee0e` via `git show`; no old JS/HTML.
- **Why**: §5 asked to reuse styles; `web/` was already deleted.
