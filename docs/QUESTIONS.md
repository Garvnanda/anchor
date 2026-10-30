# Questions for the user
Unchecked items block build-all and scheduled runs. Answer under the item, then tick it.

- [x] (Phase 5) Submission deadline (time today) and where it is submitted — decides how much of the cut list (§Phase 4 fallback) we use.
  **Answer**: ~6 hours from 2026-10-28 build start. No cuts planned; cut list applies only if behind.
- [x] (Phase 5) Vercel account ready and linked to the GitHub repo? Vercel CLI is not installed; deploy via dashboard import or `npx vercel`.
  **Answer**: user deploys (dashboard import, Root = `mvp`). Claude stops at deploy-ready after a local `npx vercel dev` check.
- [x] (Phase 1) Free RAM on this laptop ≥ 8 GB and internet available for the first model + SQuAD download?
  **Answer**: yes; use installed Python 3.12.10 (`py -3.12`) for the venv.
- [x] (all) Manual checks — when?
  **Answer**: one planned stop after Phase 2 (user spot-reads dataset rows, sees probe results). Visual approval of the site happens at the design-mock step before Phase 1 and at the end.
- [x] (all) Critical gate failure?
  **Answer**: systematic debugging, max 3 fix attempts, then stop and report. Never ship numbers from a leaky probe.
- [x] (all) Git?
  **Answer**: no `/quiz` for this project; Claude stages and commits after each passed phase. Never push, never `--no-verify`.
- [x] (Phase 4) Design and browser checks?
  **Answer**: fresh security-tool look, mock approved before Phase 1. Chrome automation allowed on localhost.

## Full product (opened 2026-10-29)
- [x] (all) Where does 3B run for training *and* serving the probe: this laptop (CPU bf16) or the RTX 2050 laptop (4-bit)? Depends on the CPU speed spike (running 2026-10-29). Must be one setup for both.
  **Answer** (G1, 2026-10-30): RTX 2050, NF4 weights + bf16 compute (measured; see `decisions.md` 2026-10-30).
- [x] (all) Code location: keep growing inside `mvp/` (no churn; Vercel root stays `mvp`) or move to a new top-level package? Recommendation: keep `mvp/` until submission.
  **Answer**: keep the code in `mvp/` (user, 2026-10-29). **Superseded later the same day:** `mvp/` stays frozen as the deployed MVP; the full product goes in a new folder (see below).
- [x] (attacks) Second held-out language (besides Hindi/Hinglish)? Recommendation: one with a different script (e.g. Tamil or Arabic) to test script transfer.
  **Answer**: Tamil (user, 2026-10-29).
- [x] (live) Pipelock install on the demo laptop: build from source (needs Go 1.26+) or verified prebuilt release (includes inactive paid-tier code)? Download needs your OK.
  **Answer**: prebuilt release (user, 2026-10-29). Installed v3.7.1 `windows_amd64` at `~/tools/pipelock/pipelock.exe` (outside the repo); SHA-256 matches the release `checksums.txt` (a06d89e2…2065); signature not checked (no cosign). Repeat on the demo laptop if it is a different machine.
- [ ] (baselines) Horizon-Labs guard and PIGuard licences: check model cards before running; gated ones need you to accept terms on Hugging Face.
- [ ] (H0) Name of the new full-product folder (written as `v2/` in the docs until H0 scaffolds it).
- [x] (G1) HF token on Garv's laptop: his own token with Llama access, or Haragam's shared privately (never via git or chat)?
  **Answer**: token is in the git-ignored `.env` on Garv's laptop; the Llama-3.2-3B download worked (2026-10-30).
