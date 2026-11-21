# Anchor dual-host delivery plan

## Product and current evidence

Build one developer-facing npm distribution (`@garvnanda/anchor-ai`) with separate OpenClaw and OpenCode entrypoints. OpenClaw is the primary integration target. OpenCode is the existing secondary integration and regression baseline. Both adapters translate host callbacks into the shared TypeScript policy, taint and audit runtime. The local server feeds one portal. Python owns managed Qwen generation, activation capture and probe scoring. The final detector-backed demonstration requires this Option A path.

The existing OpenCode audit, server, portal, contracts and Python provider are starting assets. The historical extractor and managed provider agreed exactly on layer-9 deltas for two identical-token controls. In the observed OpenCode format the historical probe caught 9/22 held-out injections and flagged 3/22 benign examples. These results apply to that profile only. See the [evaluation](ml/evaluation-report.md), [parity report](ml/parity-report.md) and [OpenCode audit](integrations/opencode-hook-audit.md).

## Execution order and acceptance evidence

| Order | Owner | Work and exit evidence |
| --- | --- | --- |
| 1. Audit the primary host | A | Pin OpenClaw, SDK, runtime and plugin manifest. Load a minimal adapter. Run a harmless read followed by a local counting sink. An allowed call increments the counter once. A denied call leaves it unchanged. Capture hook order, call IDs, grants and tool classes tested. Record unobserved paths as unknown. |
| 2. Verify the model path in parallel | B with A | Route that real OpenClaw session through the existing managed Qwen provider. Complete generation, a tool result and the next model turn. Put a harmless marker in result middleware and verify it in the provider input. Repeat with the grant absent and record actual behavior. Measure both prompt lengths, peak memory and turn latency on the demo machine. |
| 3. Freeze the demo profile | Both | Record host version, instructions, tools, model and tokenizer revisions, template, numerical precision and context limit. Start with one attributable result per turn. The prior OpenCode capture was about 10,400 tokens before tool output against an 8,192-token provider limit. Measure each host independently. If a required path fails, record the failing boundary and reconvene before committing to a different demo host. |
| 4. Integrate both adapters | A | Reuse the existing core and OpenCode audit fixtures. Coordinate a versioned contract change for host identity with B. The strict v1 source enum currently accepts `opencode_plugin`. Test old event replay, host-scoped session and call IDs, allow/block decisions, detector outages and accurate coverage reporting on each host. Verify MCP tools separately wherever coverage is claimed. |
| 5. Qualify the detector and portal | B | Use activations from actual managed generation on the frozen profile. Group related pages into the same split, fit on training data, set the threshold against the agreed benign false-alarm budget on validation, then evaluate once on untouched pages. Report caught/total injections and flagged/total benign pages separately per host. Display host, coverage, score availability and enforcement reason in the shared portal. |
| 6. Package and demonstrate | A and B | Bundle the shared core, host-specific loaders, detector client, CLI and portal in one distribution. Exports are `@garvnanda/anchor-ai/openclaw` and `@garvnanda/anchor-ai/opencode`. Verify each host's native discovery and manifest requirements with a clean install of the packed artifact. Document Python setup independently. Demonstrate a real correlated managed score, resulting policy decision and sink outcome on the primary host. Publish secondary-host capabilities only at their measured level. |

## Host contracts to verify

OpenClaw documents pre-execution blocking and pre-model tool-result middleware. Installed middleware requires explicit enablement and the matching manifest contract. Transcript persistence and model-call telemetry are different observation points. Record which runtime and tool paths actually invoke the adapter. [Host hooks](https://docs.openclaw.ai/plugins/sdk-overview/host-hooks) ? [Tool policy](https://docs.openclaw.ai/plugins/hooks/tool-policy)

Use the repository's pinned OpenCode integration for regression. A host upgrade needs a new audit because the V2 plugin API changes hook registration and lifecycle semantics. [OpenCode migration guide](https://opencode.ai/docs/build/plugins/migrate-v1)

## Decisions still open

The controlled OpenClaw demo uses read and write. A false-alarm budget and held-out qualification are still needed for host-specific scoring. Confirm registry ownership before publication.

## November 21 implementation evidence

The [judge guide](../option-a/distribution/README.md) contains the packaged commands and machine prerequisites. The installable tarball contains both adapters, the shared runtime, CLI, browser portal, validators, probe and Python provider. A clean install and Edge browser check exercised all four controlled runs.

Both native hosts completed managed Qwen tool calls. OpenClaw's real read/write experiment recorded pending-read and tainted-session denials under enforce mode. Monitor mode produced the receipt on disk. [Measured decisions and provider usage](integrations/openclaw-showcase.json)

The matched-profile Qwen controls produced a real score-backed allow and deny. The host adapters currently use exposure policy. OpenClaw's middleware marker did not reach the provider on the tested profile. Cross-host detector qualification, a primary-host decision backed by that qualified score, and registry publication remain open.
