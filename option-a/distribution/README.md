# Anchor judge showcase

From the repository root on the prepared Windows demo machine, run the packaged CLI:

```powershell
npm install --prefix option-a/.cache/showcase ./option-a/garvnanda-anchor-ai-0.1.0-demo.1.tgz
$env:ANCHOR_PYTHON = (Resolve-Path option-a/.cache/b7-verify/Scripts/python.exe).Path
& option-a/.cache/showcase/node_modules/.bin/anchor.cmd demo --qwen
```

Open the printed loopback address, enter the printed token and select a run. The token lives in memory. Ctrl+C closes the portal. Add `--check` for an unattended run.

1. Show the two policy runs. The fixture calls the OpenClaw adapter, reads an untrusted page and attempts a local receipt. Monitor records the hypothetical denial and counts one receipt. Enforce blocks before the receipt is counted.
2. Show the two matched-profile runs. Python generates a token on the original task and again with a single tool result. Anchor scores the difference between their layer-9 activations. The TypeScript runtime checks inference identity, probe provenance and threshold before allowing or denying the local receipt. Expand the detector result in the timeline. These are fixed historical-format controls. Host prompt formats require separate qualification.
3. Use the host smoke checks below to demonstrate actual agent integration. Use `anchor monitor PATH_TO_JSONL` to inspect or follow a recorded host run. Start a new audit file per demonstration.

## Install the local distribution

```powershell
npm install ./option-a/garvnanda-anchor-ai-0.1.0-demo.1.tgz
npx --no-install anchor demo --check
```

The policy demonstration runs with Node alone. For the activation demonstration, set `ANCHOR_PYTHON` to the prepared Python interpreter. Python dependencies are listed in `dist/python/requirements-windows.txt` in the installed package. The weights for Qwen/Qwen2.5-0.5B-Instruct revision `7ae557604adf67be50417f59c2c2f167def9a775` must be present in the local Hugging Face cache. `anchor provider` starts the separate authenticated loopback server and requires `ANCHOR_DETECTOR_TOKEN`. Its host-profile activation endpoint reports the existing incompatibility until a host-specific probe qualifies.

## OpenCode 2.3.2

In a project with the package installed, create `.opencode/plugins/anchor.ts` containing:

```typescript
export { default } from "@garvnanda/anchor-ai/opencode";
```

Set `ANCHOR_OBSERVATION_LOG` to an absolute file path with an existing parent. Set `ANCHOR_POLICY_MODE` to `monitor` or `enforce`. Set `ANCHOR_UNTRUSTED_TOOLS` and `ANCHOR_PROTECTED_TOOLS` to disjoint comma-separated lists of actual tool IDs. To exercise the installed adapter and managed Qwen from this repository:

```powershell
$env:ANCHOR_PACKED_OPENCODE = (Resolve-Path node_modules/@garvnanda/anchor-ai/dist/opencode/index.js).Path
node option-a/python/b1_smoke.mjs --managed
```

## OpenClaw 2026.11.6

Use Node 24.16 or newer in the 24.x line. Point `plugins.load.paths` to the absolute installed `node_modules/@garvnanda/anchor-ai` directory and explicitly enable the plugin. Set `ANCHOR_OBSERVATION_LOG` before starting the host. For a controlled workspace the relevant entry is:

```json
{"plugins":{"entries":{"anchor-ai":{"enabled":true,"config":{"mode":"enforce","protectedTools":["write"],"untrustedTools":["read"],"markToolResults":true}}}}}
```

Run the isolated host check from the repository root. It creates a temporary workspace, pins a local provider, limits the tools and records the host output and JSONL audit trail under `option-a/.cache`. Its exit status checks the audit evidence independently from the agent's final message.

```powershell
$env:ANCHOR_PACKAGE = (Resolve-Path node_modules/@garvnanda/anchor-ai).Path
& $env:ANCHOR_PYTHON option-a/python/openclaw_smoke.py enforce
```

Set `ANCHOR_NODE` and `ANCHOR_OPENCLAW` to the Node executable and OpenClaw CLI module when using different installation locations.

## Rebuild

```powershell
npm ci --prefix option-a
npm ci --prefix option-a/apps/dashboard
node option-a/distribution/build.mjs
npm pack ./option-a/distribution --pack-destination option-a
```
## Verified showcase scope

On the prepared Windows machine, the packed OpenCode 2.3.2 adapter observed tool results from an actual managed Qwen session. OpenClaw 2026.11.6 read a local file and returned the workshop time through the same provider. Its native host also produced a receipt under monitor mode and denied writes under enforce mode, including a call attempted while the read was pending. The isolated tool policy covers the listed read and write tools.

The default Qwen showcase uses the first benign and injected test rows of the historical matched profile. On this machine the measured scores were 0.0652475 and 0.9908227 at threshold 0.431316. These two examples demonstrate the mechanics of a score-backed decision. Host-specific held-out performance requires a frozen host profile, qualification data and a locked threshold. The current host demos use the shared exposure policy.

To run either real host using the installed package on this machine:

```powershell
& option-a/.cache/showcase/node_modules/.bin/anchor.cmd opencode-demo
& option-a/.cache/showcase/node_modules/.bin/anchor.cmd openclaw-demo monitor
& option-a/.cache/showcase/node_modules/.bin/anchor.cmd openclaw-demo enforce
```

The OpenClaw showcase caps the local provider at three generations because the small model sometimes retries a denied write. The test checks tool decisions, the receipt on disk and real provider continuations. It reports middleware marking independently. The observed read-only run carried the file contents through to the model, but the middleware marker was absent. Add `--require-marker` to make missing marker coverage a failing test.

From the repository root the scripts discover the pinned host binaries under `option-a/.cache`. On another machine, install the corresponding host versions and set `ANCHOR_OPENCODE` to the OpenCode executable, `ANCHOR_NODE` to Node and `ANCHOR_OPENCLAW` to OpenClaw's `openclaw.mjs`. OpenCode plugin authors using TypeScript can install the matching `@opencode/plugin@2.3.2` development types.

## Publish the npm preview

Build and pack from the repository root using the commands above. Review the exact archive before publishing. The package contains the CLI, adapters, portal, provider scripts and probe. The host executables, Python environment and Qwen weights are installed separately.

```powershell
tar -tf ./option-a/garvnanda-anchor-ai-0.1.0-demo.1.tgz
npm.cmd publish ./option-a/garvnanda-anchor-ai-0.1.0-demo.1.tgz --dry-run --access public --tag demo
npm.cmd login --registry=https://registry.npmjs.org
npm.cmd whoami --registry=https://registry.npmjs.org
npm.cmd publish ./option-a/garvnanda-anchor-ai-0.1.0-demo.1.tgz --access public --tag demo --registry=https://registry.npmjs.org
```

Enable two-factor authentication before signing in and complete the publish prompt. The `demo` tag makes the prerelease an explicit opt-in. npm rejected the unscoped `anchor-ai` name because it resembles `anchorai`. The preview uses the personal scope recommended by npm. A version already on the registry requires a version bump for a changed artifact. [npm publishing guide](https://docs.npmjs.com/creating-and-publishing-scoped-public-packages/) · [npm two-factor authentication](https://docs.npmjs.com/requiring-2fa-for-package-publishing-and-settings-modification/)

After npm accepts the publish, test the registry install from a fresh project:

```powershell
npm.cmd view @garvnanda/anchor-ai@demo version
npm.cmd install @garvnanda/anchor-ai@demo
npx.cmd anchor demo --check
```

Share the package page at `https://www.npmjs.com/package/@garvnanda/anchor-ai` once it resolves. The webpage served by the CLI is local to the machine running it. Judges can install the package and run the CLI themselves.
