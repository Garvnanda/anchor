# Implementation plan

Hackathon mode: each phase has light gates (its own tests pass + a quick smoke check). The full safety/quality
pass happens once, in Phase 7, before the demo.

Status values: `NOT STARTED` · `IN PROGRESS` · `DONE` · `BLOCKED`.

---

## Phase 0 — Model server
**Status:** DONE
**Prerequisites:** GPU with CUDA; Hugging Face access to Llama-3.2-3B-Instruct (token in `.env`, git-ignored).
**Work:** load 4-bit model, `output_hidden_states`, FastAPI (`/health`, `/score`, `/steer`).
**Done when:**
- [x] FastAPI server runs with live model (GPU + token) or mock mode (no GPU).
- [ ] VRAM and latency per call recorded on RTX 2050 (pending hardware).
- [x] Token never appears in logs or repo (secret scan passes).

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
**Prerequisites:** Phases 0, 1.
**Work:** extract Δ activations, compare layers and token positions, train linear probe, choose threshold on validation.
**Done when:**
- [ ] Layer / position choice recorded in `decisions.md` with the measured comparison.
- [ ] TPR at the chosen FPR measured on held-out documents and on the held-out style.
- [ ] Probe beats the keyword baseline, or the gap (or lack of one) is reported honestly.

## Phase 3 — Block / steer
**Status:** NOT STARTED
**Prerequisites:** Phase 2.
**Work:** block path, steering vector + forward hook, strength tuning, mode config.
**Done when:**
- [ ] Block refuses the pending action on a known-poisoned output.
- [ ] Steer reduces attack success vs. no steer; clean-task quality change measured.
- [ ] Default mode chosen and recorded.

## Phase 4 — Agent loop and scripted tools
**Status:** DONE
**Prerequisites:** Phase 0.
**Work:** loop, mock tools, vanilla and Anchor variants sharing code, turn cap.
**Done when:**
- [x] Vanilla agent leaks the planted key on the poisoned page (attack reproduces).
- [x] Anchor agent detects drift and blocks the action.
- [x] Both variants finish within the turn cap.

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
- [x] Web demo runs at localhost:8000 with side-by-side agent comparison.
- [x] Interactive scoring playground works.
- [ ] Full test suite green, 0 skipped.
- [ ] Demo runs with network off except localhost.
- [ ] Demo works twice in a row from a cold start.
- [ ] Secret scan clean on repo and packaged zip.
- [x] README has setup and run instructions.
