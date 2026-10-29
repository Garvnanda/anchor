# Security backlog
Medium/low findings from security-breaker runs. Cleared in the User simulation phase.

## Phase 3 run (2026-10-29) — mvp/api
Fixed with tests (`test_api.py`): F1 high, chunked body skipped the 2 KB cap → `BodyCap` ASGI middleware counts received bytes; F2 medium, NaN/Infinity threshold → 500 → custom 422 handler without echoed input; F3 low, `"1"` / `true` coerced → `strict=True`; F5 low, unpinned fastapi → `fastapi==0.162.0`, `starlette==1.10.0`.

Open:
- [x] F4 (low) — fixed 2026-10-29: `BodyCap` answers 422 on repeated JSON keys (`test_duplicate_json_keys_rejected`; in the sim's invalid mix). Was: duplicate JSON keys, last wins (`{"scenario_id":1,"scenario_id":2}` → scenario 2). Harmless for a stateless replay; matters only if a proxy/WAF ever inspects the first key.
- [x] F6 (low) — **risk accepted by user 2026-10-29** (local dev only). Was: local-only StaticFiles mount serves Windows aliases (`/index.html::$DATA`, `/INDEX.HTML`). Stays inside `public/`; not deployed (Vercel CDN serves `public/`).
- Note: `probe_meta.json` exposes the demo secret `sk-demo-4f2a9c` by design (shown in leak traces). Must stay obviously fake.

## Full-project run (2026-10-29, Phase 4.5) — 0 critical/high
Fixed with tests:
- [x] Content-Length of thousands of digits → `int()` ValueError → 500 (uvicorn rejects first; Vercel unknown) → length check before `int()` (`test_absurd_content_length_is_413_not_500`).
- [x] No security headers → `vercel.json` sends CSP (script hash for the inline theme script, Google Fonts only, `frame-ancestors 'none'`), nosniff, `Referrer-Policy: no-referrer`, `X-Frame-Options: DENY` (`test_vercel_security_headers_match_inline_script`; checked in headless Chrome: real hash → no violation, wrong hash → blocked).
- [x] Pins: `mvp/requirements.txt` adds pydantic/pydantic_core; `offline/requirements.txt` pinned to the venv versions (`test_offline_requirements_pinned`).

Risk accepted by user 2026-10-29 (none affects the deployed site):
- [x] Slow body (1 byte / 2 s) holds a local uvicorn connection; no body-read timeout. Vercel likely buffers bodies (unverified).
- [x] F6 above (local StaticFiles aliases).
- [x] Offline pipeline downloads the HF model (no `revision=`) and InjecAgent from the `main` branch (no commit SHA / hash). Laptop-only; parsed with `json.loads`, no pickle / `trust_remote_code`.

Verified fixed: F4 duplicate keys (nested, UTF-16, escaped-key variants all 422). Notes: Google Fonts sends visitor IPs to Google; `mvp/.pytest_cache` is not in `.vercelignore` (not under `public/`, so not served).

## Automated commit review (2026-10-29)
- [x] (medium) `RecursionError` while checking repeated JSON keys would escape `BodyCap` → 500. Not reachable in practice under the 2 KB cap (1,024-deep arrays → 422), fixed anyway: `_json_problem` returns 422 "JSON nested too deeply" (`test_too_deeply_nested_json_is_422_not_500`, `test_deepest_json_under_the_cap_is_rejected_cleanly`). Suggested "only check JSON POSTs" not applied: non-JSON bodies already pass through (`ValueError` → FastAPI's own 422).
