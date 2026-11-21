# Anchor Option A workspace

This directory contains the Developer A audit harness. The npm workspace starts here after A0 and the shared C0 contract pass.

From the repository root on Windows x64 with Node 24 and npm 11, install the pinned audit tools into the ignored cache:

```powershell
npm install --prefix option-a/.cache/audit --no-audit --no-fund --save-exact @opencode/cli@2.3.2 @opencode/plugin@2.3.2 ajv@8.17.1 ajv-formats@3.0.1
node option-a/audit/verify-contracts.mts
```

Start Ollama on loopback and run the harmless sentinel audit with a local tools-capable model:

```powershell
ollama pull qwen3:0.6b
node option-a/audit/verify.mjs
```

`ANCHOR_AUDIT_MODEL` overrides the local model tag. `ANCHOR_OPENCODE` accepts a path to the pinned Windows CLI. Evidence stays under `option-a/.cache/sentinel-*`. A run without a correlated tool attempt fails the harness. This check measures a tool hook on a harmless custom tool. The managed-Qwen demo has its own C2 gate.
