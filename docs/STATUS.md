# Status — resume point

**Date:** 2026-10-27
**Phase:** 0–7 NOT STARTED (assumption: pitch deck exists; no code or measurements confirmed). Demo / pitch date on the deck: 2026-10-30.
Update this file first if the assumption is wrong.

## Facts known (from the deck, unmeasured)
- Model: Llama-3.2-3B-Instruct, 4-bit; deck claims ~2–2.5 GB VRAM.
- Hardware: laptop RTX 2050, 4 GB.
- Probe and steering vector train on CPU "in seconds" (claim).
- No fine-tuning runs; Hugging Face hidden states + a forward hook; no closed APIs; no cloud during the demo.
- Pipelock used unmodified as the network layer.

## Measured results
None yet. Fill the table below as runs complete; deck and README may quote only this table.

| Run | Probe (layer / position) | TPR @ FPR | False-block rate | Attack success (off → on) | Latency / output | Held-out style |
|---|---|---|---|---|---|---|
| — | — | — | — | — | — | — |

## Final configuration (to freeze)
- Model: Llama-3.2-3B-Instruct, 4-bit.
- Layer, token position, threshold, mode (`block` / `steer` / `both`): **undecided**.

## Next steps
1. Phase 0: model server + VRAM / latency check on the RTX 2050.
2. Phase 1: dataset with document-level split and one held-out injection style.
3. Phase 2: probe, layer comparison, threshold on validation.
4. Phase 4 in parallel: vanilla agent reproduces the leak.
5. Phases 3, 5, 6, 7 in order; rehearse the demo twice cold before 2026-10-30.

## Pending / risks
- Probe may detect injection style or keywords rather than goal drift → held-out style test is mandatory.
- 4 GB VRAM is tight for two forward passes + hook; check batch / context limits early.
- Steering may degrade clean-task quality; measure before choosing a default.
- Attack split across several tool outputs is not covered by per-output scoring.
- Deck numbers (2–2.5 GB, "seconds") are claims until measured.

## Repo state
- Not confirmed. Record branch and uncommitted files here.
