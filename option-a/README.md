# Anchor Option A workspace

This is the TypeScript workspace for OpenCode observation, policy and the local event API. The packages use the proposed C0 schema until the joint integration check.

From this directory, install and compile the workspace:

```powershell
npm ci
npm test
```

The workspace requires Node 24 and npm 11. The core has no runtime dependencies. The OpenCode adapter targets CLI and SDK 2.3.2. It defaults to monitor mode and emits a run per observed OpenCode session. Tool output fingerprints use a process-local key and cover at most 250,000 UTF-8 bytes. The observation log contains no raw prompts, tool arguments, results or error messages.

To register the built adapter locally, use [the example plugin](examples/opencode/.opencode/plugins/anchor.ts) under `.opencode/plugins/` in a directory where `@anchor-ai/opencode` resolves. Set `ANCHOR_OBSERVATION_LOG` to an absolute file path inside an existing local directory before launching OpenCode. The live test below verifies this registration against the actual CLI.

## Audit and live integration tests

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

For A1, run `npm run test:opencode` from `option-a/` with the same local CLI and model. The test checks actual prompt and tool result observation, validates emitted events against C0, and compares tool and session IDs against the independent sentinel trace under `.cache/a1-live-*`.

For A3, run `npm run test:policy-demo` from `option-a/`. The policy-only fixture uses a synthetic value and writes any receipt into the isolated run directory. The comparison requires an actual matching agent attempt in both modes. If the agent only reads or summarizes the page, the result is inconclusive.

The [local portal example](examples/portal/.opencode/plugins/anchor.ts) publishes directly from the same process as the policy runtime and serves the C0 API at `http://127.0.0.1:8080`. Register it in place of the observation example, set a locally generated `ANCHOR_PORTAL_TOKEN`, and send it in the `Authorization: Bearer …` header. The authenticated `/diagnostics` route reports retained runs, events and clients. Coverage defaults to unknown until the operator supplies verified evidence. The HTTP detector client has loopback health, metadata and activation lookups. Direct generation correlation with Garv's service is verified at C1.
