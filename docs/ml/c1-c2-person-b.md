# Person B checkpoint handoff

The frozen contracts are at `c4adfab7f6f23d1273384caa5b00fc0d76d3b863`. The Python C0 validator again matched all ten shared fixture expectations.

## C1 provider handshake

Run `python -B tests/python/test_managed_transport.py -v` with the prepared managed environment as described in the [integration guide](detector-integration.md). The independent HTTP client starts the authenticated provider, submits two tool results in one genuine Qwen generation, validates the returned detector records and checks each run, session, inference and tool ID. Both records report incompatible with null scores. Malformed input, partial IDs and duplicate or ambiguous calls are rejected. Unknown lookup returns 404. A competing generation returns 503 while health remains available. A bounded client timeout and process loss are observable by the caller.

The recovery test starts a fresh provider process after termination. The old pair returns 404, health reports incompatible, and both health and metadata validate against the response schemas in the frozen OpenAPI document. Earlier startup tests cover invalid model and probe hashes, missing assets and unauthorized requests.

A joint C1 run still requires the real A-side client, policy record and protected action. The acceptance evidence must show matched IDs, a measured end-to-end deadline, and an independently observed suppressed side effect. B2 remains the prerequisite for the compatible direct-score path.

## C2 benign and failure controls

Run `node option-a/python/b1_smoke.mjs --managed` to start the packaged authenticated service and point OpenCode 2.3.2 at its loopback endpoint. The test creates a per-run bearer credential. It checks two actual completed tool hooks with empty arguments, at least two model generations, and both returned colors in the CLI output. The provider writes redacted event types. The diagnostic capture harness separately records IDs for activation tracing.

The single-result diagnostic trace was rechecked against the provider and hook logs. Baseline `chatcmpl-adc792e3fd5c4739a7c69a4631085167` emitted `call_98cb100cfb0f413b9958fd12b7e57baf`. The completed OpenCode hook and subsequent tool result carried that ID, and the recorded activation points to continuation `chatcmpl-e177cde8d9ef4e9589cc49b51f469d2b`. Its score remains experimental under the [B2 findings](parity-report.md).

The browser control exercises all eleven event kinds against a fixture server, including cursor loss and history recovery. Clean Windows installation and service restart are verified. Release rollback, live portal events, independent sink receipts and a detector-backed OFF/ON comparison remain joint acceptance items. Record both modes' provider identity, correlated tool attempts and sink receipts when the integration exists. The benign color tools provide no sink or enforcement evidence.
