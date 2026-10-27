# Status — resume point

**Date:** 2026-10-28
**Phase:** Demo scaffold complete; core detection not built. Scaffold code then **deleted** (2026-10-28) to rebuild the MVP from these docs. Repo holds docs only.

## Facts known
- Model: Llama-3.2-3B-Instruct, 4-bit; deck claims ~2–2.5 GB VRAM.
- Hardware target: laptop RTX 2050, 4 GB.
- Probe and steering vector train on CPU "in seconds" (claim, unmeasured).
- No fine-tuning; Hugging Face hidden states + a forward hook; no closed APIs; no cloud during the demo.
- Pipelock used unmodified as the network layer.

## What the removed scaffold did (deleted locally; not to be restored)
- Model server (`/health`, `/score`, `/steer`, `/demo`) with live or mock mode.
- Agent actions were **fully scripted** — the model did not choose them.
- Live scoring was the **L2 norm of Δ through a fixed sigmoid**, not a probe.
- `/steer` was a **stub** in live mode.
- Web demo (side-by-side + scoring playground) read the `/demo` JSON response.
- Tests: 8 (server endpoints + secret scan), mock scorer only.

## Known issues (in the removed scaffold — the rebuild must not repeat them)
- Anchor agent may leak in mock mode: block decision scored on the email text, not the poisoned page.
- Last-token read without chat template.
- Norm score grows with output length, so clean long pages may be flagged.
- Silent fallback to mock.
- Tests cover the mock keyword filter only.

## Measured results
None from the real model yet.

| Run | Probe (layer / position) | TPR @ FPR | False-block rate | Attack success (off → on) | Latency / output | Held-out style |
|---|---|---|---|---|---|---|
| — | — | — | — | — | — | — |

## Final configuration (to freeze)
- Model: Llama-3.2-3B-Instruct, 4-bit.
- Read position: assistant-turn start token, chat template (see `decisions.md`).
- Layer, threshold, mode (`block` / `steer` / `both`): **undecided** — requires GPU runs.

## Next steps
1. Taint fix: score attached to the tool output; high score taints the run; later side-effecting actions blocked.
2. Chat-template read: user = task, tool = output, hidden state at assistant-turn start token.
3. Rebuild MVP: model server (sync handlers + GPU lock, loud mock / `ANCHOR_REQUIRE_LIVE`), agent loop, `main.py demo`, tests (Phase 0, 0.5, 4).
4. Model generates the email action (not scripted) — model-driven agent mode.
5. Run model server on RTX 2050 with real HF_TOKEN — measure VRAM and latency.
6. Build dataset with document-level split and held-out injection style.
7. Train drift probe, compare layers, choose threshold on validation.
8. Compute steering vector, implement live `/steer`, measure clean-task quality impact.
9. Full evaluation pass, write report.
10. Integrate Pipelock as Layer 2.
11. Rehearse demo twice cold before pitch date.

## Repo state
- Repo `anchor/` (remote `github.com/haragam22/anchor`). Local tree: `README.md`, `.gitignore`, `docs/` only.
- `code/`, `web/`, `.env.example` deleted from disk; docs + README refactored. Not yet committed or pushed (user pushes later).
