# Simulated users (Phase 4.5)

`python sim/simulate.py` (from `mvp/`, project venv) — 1,000 seeded users against the replay API (in-process
FastAPI TestClient, same app object Vercel serves). Seed 0; deterministic.

## Input mix (per user: one session of 3–8 actions)
| Share | Action | Expected |
|---|---|---|
| ~15 % | `GET /api/health` | 200, `mode: replay` |
| ~10 % | `GET /api/scenarios` | 200, 8 items |
| ~10 % | `GET /api/metrics` | 200, equals `offline/out/metrics.json` |
| ~55 % | `POST /api/run` valid: random scenario; threshold = none / uniform [0,1] / edge (0, 1, val threshold, threshold ± 1e-6) | 200; every defence's verdict equals an independent re-computation of the taint rule from `api/data/scenarios.json` |
| ~10 % | invalid: unknown id, threshold < 0 or > 1, NaN, string, missing body, extra field, malformed JSON, oversized body, wrong method, unknown path | 4xx (never 5xx, never 200) |

## Pass bar
0 crashes / 5xx / unhandled exceptions · valid-input error rate < 1 % · 100 % of invalid inputs rejected with 4xx ·
every valid `/api/run` matches the independent re-computation · p95 latency < 200 ms (in-process).
