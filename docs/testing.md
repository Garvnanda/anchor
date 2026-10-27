# Testing

## Automated
- `python -m pytest code/tests -q` — unit tests (added per phase).
- `python code/evaluation/main.py` — probe + agent scoring (Phase 6).

Unit tests fake only external boundaries (GPU model call, Pipelock process, clock). No network in tests.

## Evaluation (local model, no paid calls)
- `python code/evaluation/main.py --run-name eval_vN` — prints TPR at fixed FPR, false-block rate, attack success
  with / without Anchor, latency per tool output, VRAM; per injection style and per language; writes
  `code/evaluation/evaluation_report.md`. Use a new run name per probe / threshold change.
- Splits are by document and injection style; the held-out style is never used for tuning.
- Baselines always reported: no defence, keyword filter.

## Behaviour checks
- Vanilla agent leaks the planted key on the poisoned page; agent + Anchor does not.
- Clean pages: Anchor does not block (false-block rate reported, not assumed zero).
- Injection text aimed at the checker ("ignore the drift check") does not change the score path.
- Model server killed mid-run: action is blocked, not allowed.
- Pipelock off: Anchor alone stops the demo attack. Anchor off: Pipelock alone stops the direct exfiltration attempt.

## Security regression tests
- `code/tests/test_secrets.py` — no token or planted demo key in repo, logs or package.
- `code/tests/test_fail_closed.py` — server down, OOM, score error → action blocked.
- `code/tests/test_pipelock_untouched.py` — Pipelock files unchanged (version / hash).

## Manual checks
- `python code/model/smoke.py` → prints one generation, hidden-state shape, VRAM, latency.
- Demo from a cold start, twice, with the network off except localhost.
- Packaged zip: inspect names, scan for the token and for model weights.

## Packaging
- `python code/package.py [--out code.zip]` — README + code without caches, weights, `.env`.

Add new commands and manual checks here as they are created.
