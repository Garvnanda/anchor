# Status — resume point

**Date:** 2026-10-27
**Phase:** MVP complete (model server, agent loop, web demo, tests). Probe / steering / evaluation use mock scoring — live model integration pending GPU hardware.

## Facts known
- Model: Llama-3.2-3B-Instruct, 4-bit; deck claims ~2–2.5 GB VRAM.
- Hardware target: laptop RTX 2050, 4 GB.
- Probe and steering vector train on CPU "in seconds" (claim, unmeasured).
- No fine-tuning; Hugging Face hidden states + a forward hook; no closed APIs; no cloud during the demo.
- Pipelock used unmodified as the network layer.

## What works today
- Model server (`/health`, `/score`, `/steer`, `/demo`) — live mode with real model or deterministic mock mode without GPU/token.
- Agent loop — vanilla agent leaks the planted secret; Anchor agent detects drift and blocks.
- Web demo — side-by-side comparison + interactive scoring playground at `localhost:8000`.
- Tests — 8/8 passing (server endpoints + security regression).

## Measured results
None from the real model yet. Mock mode validates the full pipeline end-to-end.

| Run | Probe (layer / position) | TPR @ FPR | False-block rate | Attack success (off → on) | Latency / output | Held-out style |
|---|---|---|---|---|---|---|
| — | — | — | — | — | — | — |

## Final configuration (to freeze)
- Model: Llama-3.2-3B-Instruct, 4-bit.
- Layer, token position, threshold, mode (`block` / `steer` / `both`): **undecided** — requires GPU runs.

## Next steps
1. Run model server on RTX 2050 with real HF_TOKEN — measure VRAM and latency.
2. Build dataset with document-level split and held-out injection style.
3. Train drift probe, compare layers, choose threshold on validation.
4. Compute steering vector, measure clean-task quality impact.
5. Full evaluation pass, write report.
6. Integrate Pipelock as Layer 2.
7. Rehearse demo twice cold before pitch date.

## Repo state
- Branch: `main`, pushed to `github.com/haragam22/anchor`.
- All files tracked, no uncommitted changes.
