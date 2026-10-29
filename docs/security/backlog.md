# Security backlog
Medium/low findings from security-breaker runs. Cleared in the User simulation phase.

## Phase 3 run (2026-10-29) — mvp/api
Fixed with tests (`test_api.py`): F1 high, chunked body skipped the 2 KB cap → `BodyCap` ASGI middleware counts received bytes; F2 medium, NaN/Infinity threshold → 500 → custom 422 handler without echoed input; F3 low, `"1"` / `true` coerced → `strict=True`; F5 low, unpinned fastapi → `fastapi==0.162.0`, `starlette==1.10.0`.

Open:
- [ ] F4 (low) — duplicate JSON keys, last wins (`{"scenario_id":1,"scenario_id":2}` → scenario 2). Harmless for a stateless replay; matters only if a proxy/WAF ever inspects the first key.
- [ ] F6 (low) — local-only StaticFiles mount serves Windows aliases (`/index.html::$DATA`, `/INDEX.HTML`). Stays inside `public/`; not deployed (Vercel CDN serves `public/`).
- Note: `probe_meta.json` exposes the demo secret `sk-demo-4f2a9c` by design (shown in leak traces). Must stay obviously fake.
