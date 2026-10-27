# Implementation plan — post-MVP roadmap

> **Not the active plan.** The workflow hooks track `docs/implementation_mvp.md`. This file is the full-product
> roadmap (Llama-3.2-3B on GPU, steering, Pipelock) picked up after the MVP ships. Its status markers are
> informational and are converted to the hook format when it becomes active.

Hackathon mode: each phase has light gates (its own tests pass + a quick smoke check). The full safety/quality
pass happens once, in Phase 7, before the demo.

Status values: `NOT STARTED` · `IN PROGRESS` · `DONE` · `BLOCKED`.

> 2026-10-28: scaffold code deleted to rebuild the MVP. Items marked *(rebuild)* were met by the removed
> scaffold and must be met again by the new code before they count.

---

## Phase 0 — Model server
**Status:** DONE *(rebuild)*
**Prerequisites:** GPU with CUDA; Hugging Face access to Llama-3.2-3B-Instruct (token in `.env`, git-ignored).
**Work:** load 4-bit model, `output_hidden_states`, FastAPI (`/health`, `/score`, `/steer`, `/demo`).
**Done when:**
- [x] FastAPI server runs with live model (GPU + token) or mock mode (no GPU). *(rebuild)*
- [ ] VRAM and latency per call recorded on RTX 2050 (pending hardware).
- [x] Token never appears in logs or repo (secret scan passes). *(rebuild)*
- [ ] Loud mock banner / `ANCHOR_REQUIRE_LIVE`.

## Phase 0.5 — Correctness fixes
**Status:** NOT STARTED
**Prerequisites:** Phase 0.
**Work:** fix the design flaws found in the scaffold (see `STATUS.md` → Known issues).
**Done when:**
- [ ] Taint logic: high score on a tool output taints the run; later side-effecting actions blocked.
- [ ] Chat-template read position: user = task, tool = output, hidden state at assistant-turn start token.
- [ ] Sync handlers + one GPU lock.
- [ ] Test asserts Anchor agent `secret_leaked is False`.

## Phase 1 — Dataset
**Status:** NOT STARTED
**Prerequisites:** Phase 0 optional; none required.
**Work:** clean + injected tool outputs, several injection styles, document-level split, labels and provenance.
**Done when:**
- [ ] Row counts per label and per injection style written to `code/data/README.md`.
- [ ] No document appears in both train and test.
- [ ] At least one held-out injection style exists for transfer testing.

## Phase 2 — Drift probe
**Status:** NOT STARTED
**Prerequisites:** Phases 0, 0.5, 1.
**Work:** extract Δ activations, compare layers (and assistant-start vs. last-token position), train linear probe, choose threshold on validation.
**Done when:**
- [ ] Layer / position choice recorded in `decisions.md` with the measured comparison.
- [ ] TPR at the chosen FPR measured on held-out documents and on the held-out style.
- [ ] Probe beats the keyword baseline, or the gap (or lack of one) is reported honestly.

## Phase 3 — Block / steer
**Status:** NOT STARTED
**Prerequisites:** Phase 2.
**Work:** block path, steering vector + forward hook, strength tuning, mode config.
**Done when:**
- [ ] Block refuses the pending side-effecting action on a tainted run.
- [ ] `/steer` live implementation (it was a stub in the scaffold).
- [ ] Steer reduces attack success vs. no steer; clean-task quality change measured.
- [ ] Default mode chosen and recorded; `ANCHOR_MODE` wired up.

## Phase 4 — Agent loop and tools
**Status:** IN PROGRESS
**Prerequisites:** Phase 0.
**Work:** loop, mock tools, vanilla and Anchor variants sharing code, turn cap, scripted and model-driven modes.
**Done when:**
- [ ] Vanilla agent leaks the planted key on the poisoned page (attack reproduces) — scaffold version was scripted, does not count.
- [ ] Model-driven action: after reading the page the model generates the next action (tool + args).
- [ ] Anchor agent detects drift and blocks the action. *(rebuild)*
- [ ] Anchor agent verified not leaking by test.
- [ ] Both variants finish within the turn cap. *(rebuild)*

## Phase 5 — Integration with Pipelock
**Status:** NOT STARTED
**Prerequisites:** Phases 3, 4; Pipelock installed.
**Work:** route outbound requests through Pipelock; no changes to Pipelock itself.
**Done when:**
- [ ] Pipelock blocks a direct exfiltration attempt when Anchor is off.
- [ ] Both layers on: logs show which layer stopped which attack.
- [ ] Pipelock source unchanged (hash or version recorded).

## Phase 6 — Evaluation
**Status:** NOT STARTED
**Prerequisites:** Phases 2–5.
**Work:** metrics, baselines, per-style and per-language breakdown, latency, VRAM.
**Done when:**
- [ ] `python code/evaluation/main.py` writes `code/evaluation/evaluation_report.md`.
- [ ] Numbers in the report are the only numbers used in the deck and README.

## Phase 7 — Demo, web page, pre-demo checks
**Status:** IN PROGRESS
**Prerequisites:** Phases 0–6.
**Work:** web demo (two agents side by side, drift-score trace), README, offline run check, secret scan.
**Done when:**
- [ ] Web demo runs at localhost:8000 with side-by-side agent comparison. *(rebuild)*
- [ ] Interactive scoring playground works. *(rebuild)*
- [ ] UI shows live / mock mode badge.
- [ ] Full test suite green, 0 skipped.
- [ ] Demo runs with network off except localhost.
- [ ] Demo works twice in a row from a cold start.
- [ ] Secret scan clean on repo and packaged zip.
- [x] README has setup and run instructions.
