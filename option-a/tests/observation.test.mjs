import assert from "node:assert/strict";
import test from "node:test";
import { ObservationRuntime } from "@anchor-ai/core";
import { validateEvent } from "./contract.mjs";

test("interleaved sessions keep independent run IDs and sequence, with redacted output", () => {
  const events = [];
  const runtime = new ObservationRuntime(event => events.push(event));
  const a = { sessionId: "session-a", toolCallId: "call-1", toolName: "read" };
  const b = { ...a, sessionId: "session-b" };
  const output = "Ω".repeat(125_001);
  runtime.observePrompt(a.sessionId, "private prompt");
  runtime.observeToolCall(a);
  runtime.observePrompt(b.sessionId, "private prompt");
  runtime.observeToolCall(b);
  runtime.observeToolResult(b, { status: "error" });
  runtime.observeToolResult(a, { status: "completed", content: output });
  runtime.close();
  for (const event of events) assert.ok(validateEvent(event), JSON.stringify(validateEvent.errors));
  const [first, second] = [a, b].map(call => events.filter(event => event.sessionId === call.sessionId));
  assert.deepEqual(first.map(e => e.kind), ["run_started", "tool_pre_execution", "tool_output_observed", "tool_finished", "run_closed"]);
  assert.deepEqual(second.map(e => e.kind), ["run_started", "tool_pre_execution", "tool_finished", "run_closed"]);
  assert.notEqual(first[0].runId, second[0].runId);
  for (const run of [first, second]) {
    assert.ok(run.every(e => e.runId === run[0].runId));
    assert.deepEqual(run.map(e => e.sequence), run.map((_, index) => index + 1));
  }
  assert.equal(first[2].details.byteCount, Buffer.byteLength(output));
  assert.equal(first[2].details.truncated, true);
  assert.doesNotMatch(JSON.stringify(events), /private prompt|Ω/);
});
