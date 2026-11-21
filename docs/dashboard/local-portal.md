# Local portal verification

> **Current direction (2026-11-21).** The planned portal identifies the host and its measured coverage for each run. [Dual-host delivery plan](../dual-host-plan.md)

The dashboard source and its isolated npm lock are under `option-a/apps/dashboard`. The production build is static HTML, JavaScript and CSS. From that directory run:

```powershell
npm ci
node build.mjs --fixtures
npm test
node browser-check.mjs
npm run build
```

The browser check defaults to Edge on Windows. Set `ANCHOR_BROWSER` to the path of another Chromium executable when needed. The test uses a temporary local HTTP server with contract fixtures, synthetic health, coverage, snapshots and SSE. It exercises all eleven event kinds, late ordering, a streamed duplicate on reconnection, mobile overflow and keyboard disclosure. Unit checks cover null or mismatched detector scores, out-of-order arrival and split SSE frames.

The production entry is `dist/index.html`. Serve it from the same origin as the A-owned API; the application uses relative paths and an in-memory bearer token. Development fixture mode requires a loopback origin, an explicit query parameter, and a fixture-enabled build. The read-only UI exposes coverage and the original event evidence. Acceptance with real runtime events, real sink receipts and the distributed CLI requires A4/A5.
