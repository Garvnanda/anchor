# Detector integration checks

Start the authenticated loopback service with the Windows setup procedure in the developer guide. For a primary generation, send a fresh X-Anchor-Inference-Request-Id together with X-Anchor-Run-Id and X-Anchor-Session-Id. Supply the local bearer credential on both generation and lookup. A successful correlated chat completion returns the supplied inference ID as its response ID.

A tool continuation must contain a unique matching assistant tool-call declaration for each tool result. The service associates results from the final tool-call group with this generation. Partial headers, duplicate retained inference IDs and ambiguous calls receive HTTP 400. A concurrent generation receives HTTP 503 while metadata, health and lookups remain accessible. The service retains the last 512 correlated request entries in process memory. Unknown or evicted pairs receive HTTP 404.

Look up each result at `/v1/activations/{inferenceRequestId}?toolCallId={toolCallId}`. With the current probe, a completed known pair returns a contract-valid incompatible result with a null score and the PROBE_CONTEXT_INCOMPATIBLE code. The client must match run, session, request and tool IDs and apply its agreed deadline. Responses from a stopped process, a timeout, and unavailable or incompatible evidence require the A-owned enforcement decision. C1 must verify that decision independently.

## Regression commands

From the repository root, run the independent schema and real-process checks. ANCHOR_PYTHON can point the real-process test at a prepared managed Python environment. The test driver uses a Python installation with jsonschema.

```powershell
python -B tests/python/test_c0_contract.py -v
python -B tests/python/test_managed_transport.py -v
```

The transport test uses synthetic client messages and performs a real Qwen generation. It checks schema validation for two tool results, invalid and duplicate identities, cross-session reuse, unknown lookup, concurrent health, a bounded client timeout, provider busy response and service loss. The separate B1 smoke harness verifies OpenCode-generated tool calls.
