import assert from "node:assert/strict";
import test from "node:test";
import { ObservationRuntime } from "@anchor-ai/core";
import { validateEvent } from "./contract.mjs";

const event = (sessionId, toolName, toolCallId = toolName) => ({ sessionId, toolName, toolCallId });
const source = (sessionId = "one", toolCallId = "page") => event(sessionId, "page", toolCallId);
const sink = (sessionId = "one", toolCallId = "sink") => event(sessionId, "sink", toolCallId);
const options = { mode: "enforce", protectedTools: ["sink"], untrustedTools: ["page"] };
const pin = {
  modelId: "test", modelRevision: "fixed", probeHash: "a".repeat(64), featureExtractionHash: "b".repeat(64),
  layer: 9, precision: "fp32", provenanceType: "generation_forward_pass",
};
const ready = identity => ({ ...identity, schemaVersion: 1, detectorMode: "direct_managed_qwen",
  status: "ready", provenance: pin, score: 0.1, threshold: 0.5, latencyMs: 1, errorCode: null });
function direct(lookup, timeoutMs = 1000) {
  return { ...options, taintOnExposure: false, detector: { timeoutMs, provenance: pin, threshold: 0.5, lookup } };
}
function expose(runtime, call = source()) {
  runtime.observeToolCall(call);
  runtime.observeToolResult(call, { status: "completed", content: "synthetic untrusted output" });
}
async function attempt(runtime, call, execute) {
  const decision = await runtime.beforeTool(call);
  if (!decision.enforced) execute();
  return decision;
}

test("a pending or completed untrusted read prevents the protected effect without crossing sessions", async () => {
  const events = [];
  const runtime = new ObservationRuntime(event => events.push(event), options);
  const receipts = [];
  const write = () => receipts.push("receipt");
  runtime.observePrompt("one", "task");
  runtime.observePrompt("two", "task");
  assert.equal((await attempt(runtime, sink("absent"), write)).reasonCode, "MISSING_RUN");
  assert.equal((await runtime.beforeTool(source())).verdict, "allow");
  assert.equal((await attempt(runtime, sink("one", "pending"), write)).reasonCode, "PENDING_TOOL_OUTPUT");
  runtime.observeToolResult(source(), { status: "completed", content: "page" });
  assert.equal((await attempt(runtime, sink(), write)).reasonCode, "TAINTED_SIDE_EFFECT");
  assert.equal((await runtime.beforeTool(source("one", "second-read"))).verdict, "allow");
  assert.deepEqual(receipts, []);
  assert.equal((await attempt(runtime, sink("two"), write)).verdict, "allow");
  assert.equal((await attempt(runtime, sink("two"), write)).reasonCode, "CALL_ALREADY_CHECKED_OR_LIMIT");
  assert.deepEqual(receipts, ["receipt"]);
  for (const value of events) assert.ok(validateEvent(value), JSON.stringify(validateEvent.errors));
});

test("authorization rejects missing, stale, and failed detector evidence", async () => {
  const cases = [
    ["DETECTOR_UNCORRELATED", async id => ready(id), false],
    ["DETECTOR_PROVENANCE_MISMATCH", async id => ({ ...ready(id), provenance: { ...pin, probeHash: "c".repeat(64) } }), true],
    ["DETECTOR_IDENTITY_MISMATCH", async id => ({ ...ready(id), inferenceRequestId: "other" }), true],
    ["DETECTOR_TRANSPORT_ERROR", async () => { throw new Error("worker crash"); }, true],
    ["DETECTOR_TIMEOUT", () => new Promise(() => {}), true],
    ["DETECTOR_MALFORMED", async id => ({ ...ready(id), score: Number.NaN }), true],
    ["DETECTOR_THRESHOLD", async id => ({ ...ready(id), score: 0.5 }), true],
    ["CLEAN_RUN", async id => ready(id), true],
  ];
  for (const [reason, lookup, link] of cases) {
    const events = [];
    const runtime = new ObservationRuntime(e => events.push(e), direct(lookup, reason === "DETECTOR_TIMEOUT" ? 25 : 1000));
    runtime.observePrompt("one", "task");
    expose(runtime);
    if (link) assert.equal(runtime.linkInference("one", "page", "req"), true);
    let invoked = 0;
    assert.equal((await attempt(runtime, sink(), () => invoked++)).reasonCode, reason);
    assert.equal(invoked, reason === "CLEAN_RUN" ? 1 : 0);
    for (const value of events) assert.ok(validateEvent(value), JSON.stringify(validateEvent.errors));
  }
});

test("a new exposure invalidates an in-flight score and a failing observer cannot bypass denial", async () => {
  let deliver;
  const runtime = new ObservationRuntime(() => { throw new Error("store offline"); },
    direct(id => new Promise(resolve => { deliver = () => resolve(ready(id)); })));
  runtime.observePrompt("one", "task");
  expose(runtime);
  runtime.linkInference("one", "page", "req");
  const pending = attempt(runtime, sink(), () => assert.fail("sink called after invalidated score"));
  expose(runtime, source("one", "new-exposure"));
  deliver();
  assert.equal((await pending).reasonCode, "STATE_CHANGED_DURING_SCORE");
});

test("OFF requires an isolated demo and monitor decisions remain hypothetical", async () => {
  assert.throws(() => new ObservationRuntime(() => {}, { ...options, mode: "off" }), /isolated demo/);
  for (const mode of ["off", "monitor"]) {
    const runtime = new ObservationRuntime(() => {}, { ...options, mode, isolatedDemo: true });
    runtime.observePrompt("one", "task");
    expose(runtime);
    let invoked = 0;
    const decision = await attempt(runtime, sink(), () => invoked++);
    assert.deepEqual(decision, { verdict: "block", reasonCode: "TAINTED_SIDE_EFFECT", enforced: false });
    assert.equal(invoked, 1);
  }
});
