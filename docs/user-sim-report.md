# User simulation report — MVP Phase 4.5
2026-10-29. Harness: `mvp/sim/simulate.py`; input mix: `mvp/sim/users.md`.

## Setup
- 1,000 seeded users (seed 0), each a session of 3–8 actions: health / scenarios / metrics / `/api/run` with
  random, edge (0, 1, val threshold ± 1e-6) or default thresholds, and ~10 % invalid inputs (unknown id,
  out-of-range / NaN / Infinity / string / bool values, missing body, extra field, repeated JSON key, malformed
  JSON, oversized body with Content-Length and chunked without it, wrong method, unknown path, array body).
- Oracle: every valid `/api/run` is compared with an independent re-implementation of the taint rule
  (`expected_verdicts`, not imported from the API); `tests/test_sim.py` checks the oracle against the API on all
  9 scenarios at 7 thresholds, and that each invalid input gets a 4xx.
- Two targets: in-process (`TestClient`, the same `app` object Vercel serves) and real HTTP
  (`--url http://127.0.0.1:8822`, `uvicorn api.index:app`).

Pass bar (users.md): 0 crashes / 5xx / unhandled exceptions · valid-input error rate < 1 % · 100 % of invalid
inputs rejected with 4xx · every valid `/api/run` matches the oracle · p95 < 200 ms.

## Rounds
| Round | Target | Requests | Failures | Invalid rejected | p95 | Pass |
|---|---|---|---|---|---|---|
| 1 | in-process | 5,489 | 0 | 566/566 | 15.2 ms | yes |
| 2 (repeated-key input added, F4 fix) | in-process | 5,515 | 0 | 556/556 | 11.9 ms | yes |
| 3 | HTTP, server started before the F4 fix | 5,515 | 25 `invalid_accepted` | 531/556 | 4.5 ms | no |
| 4 | HTTP, restarted on current code | 5,515 | 0 | 556/556 | 4.9 ms | yes |
| 5 (after full-project security fixes: Content-Length length check, headers, pins) | in-process + HTTP | 5,515 each | 0 | 556/556 | 14.5 / 4.5 ms | yes |

## Failure clusters
- **Round 3, repeated JSON key accepted (25)** — all 25 were `{"scenario_id": 1, "scenario_id": 2}` → 200.
  Cause: the uvicorn process had been started before the F4 fix (no `--reload`), so it served old code.
  Reproducing test: `test_api.py::test_duplicate_json_keys_rejected` (fails on the old code). Fixed in code
  (`_has_duplicate_keys` in `BodyCap`); round 4 on a restarted server passes.
- No crashes, 5xx or verdict mismatches in any round.

Before the sim, the Phase 3 security run had found the chunked-body bypass (F1); the sim now includes that input
and it is rejected with 413 both in-process and over HTTP.

## Remaining risks
- The sim targets a local server; production (Vercel) adds its own body limit and cold starts. Re-run with
  `--url <deployment>` after deploy (Phase 5) to check the deployed app with the same sessions.
- Latency numbers are local (no network); they only show the API does no heavy work per request.
- The browser UI is not part of the sim; it is covered by `tests/browser_check.js` (run by hand).
