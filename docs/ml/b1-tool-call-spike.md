# B1 managed Qwen tool-call spike

OpenCode CLI 2.3.2 used the `anchor-b1` OpenAI-compatible provider with an explicit model selection and a loopback base URL. The Python process loaded the approved `Qwen/Qwen2.5-0.5B-Instruct` snapshot in CPU FP32 with offline loading. The probe was outside the scope of this test.

## Reproduce on Windows

From the repository root, with the B0 model snapshot and a Python environment containing torch and Transformers available:

```powershell
npm install --prefix option-a/.cache/b1 --no-audit --no-fund --save-exact @opencode/cli@2.3.2
node option-a/python/b1_smoke.mjs
```

The harness defaults to the existing `v2/offline/.venv` Python and the standard Hugging Face cache. Set `ANCHOR_PYTHON` or `ANCHOR_OPENCODE` to select a different executable. The CLI version is checked before starting. The smoke plugin exposes only two harmless no-argument color tools. Each run writes local evidence under `option-a/.cache/b1-smoke-*`. The provider evidence records roles, tool names, IDs, token counts and timing without storing request bodies. This harness uses loopback with synthetic data. Authentication and per-request correlation headers belong to the later integration path.

## Observed result

| Generation | OpenCode request | Qwen response | Provider elapsed |
| --- | --- | --- | --- |
| 1 | SSE requested. System and user roles. 6,248 prompt tokens. | Emitted both tool names with empty argument objects. 34 completion tokens. | 26.07 s |
| 2 | SSE requested. System, user, assistant and two tool roles. 6,311 prompt tokens. | Replied that the first color was blue and the second green. 13 completion tokens. | 25.76 s |

The provider encoded the actual Qwen tool output into OpenAI-compatible responses and assigned an ID to each parsed call. Both IDs matched the corresponding OpenCode `execute.after` hook IDs and the tool result IDs returned in the follow-up request. Evidence was captured for one smoke scenario. The full integration header path, retries and ambiguity handling remain open for verification.

Model and tokenizer load took 5.61 s after imports. The synchronous spike generates the whole turn before sending SSE chunks. Its timing includes both prefill and decoding, and peak memory was not instrumented. The roughly 26 s generations are input for the C1 timing budget. General reliability and real-time streaming remain unmeasured.

B2 must compare the initial and post-tool generation contexts with the historical feature definition. OpenCode supplied thousands of prompt tokens and two tool results in one continuation. That differs from the MVP prompt used in B0, so compatibility of the resulting feature vectors and score still needs evidence.
