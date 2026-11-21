import assert from "node:assert/strict";
import { createServer } from "node:http";
import { once } from "node:events";
import test from "node:test";
import { ObservationRuntime } from "@anchor-ai/core";
import { createHttpDetector, createLocalServer } from "@anchor-ai/server";
import { responseContract } from "../packages/server/dist/contracts.js";

const token = "synthetic-contract-test-token";
const headers = { authorization: "Bearer " + token };
const sig = () => AbortSignal.timeout(3000);

async function openSse(service, extraHeaders = {}) {
  const response = await fetch(service.origin + "/api/events/stream", { headers: { ...headers, ...extraHeaders }, signal: sig() });
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type"), /^text\/event-stream/);
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  return {
    close: () => reader.cancel(),
    async next() {
      for (;;) {
        const boundary = buffer.indexOf("\n\n");
        if (boundary >= 0) {
          const frame = buffer.slice(0, boundary);
          buffer = buffer.slice(boundary + 2);
          const data = frame.split("\n").find(line => line.startsWith("data: "));
          if (data) return JSON.parse(data.slice(6));
        } else {
          const chunk = await reader.read();
          assert.ok(!chunk.done, "SSE closed before expected event");
          buffer += decoder.decode(chunk.value, { stream: true });
        }
      }
    },
  };
}

test("loopback API streams runtime events and resumes after disconnect", async () => {
  const api = await createLocalServer({ token, capacity: 5 });
  const call = { sessionId: "session-a", toolName: "page", toolCallId: "read-call" };
  const sink = { sessionId: "session-a", toolName: "sink", toolCallId: "sink-call" };
  const runtime = new ObservationRuntime(api.publish, { mode: "enforce", protectedTools: ["sink"], untrustedTools: ["page"] });
  const get = (path, options = headers) => fetch(api.origin + path, { headers: options, signal: sig() });
  try {
    assert.equal((await get("/api/health", {})).status, 401);
    assert.equal((await get("/api/health", { ...headers, origin: "https://example.invalid" })).status, 403);
    for (const route of ["/api/health", "/api/coverage", "/api/runs"]) {
      const response = await get(route);
      assert.equal(response.status, 200);
      assert.ok(responseContract(route)(await response.json()), route + " must match OpenAPI");
    }
    const first = await openSse(api);
    runtime.observePrompt(call.sessionId, "synthetic task");
    const opened = await first.next();
    assert.equal(opened.kind, "run_started");
    await first.close();

    await runtime.beforeTool(call);
    runtime.observeToolResult(call, { status: "completed", content: "synthetic page" });
    const resumed = await openSse(api, { "Last-Event-ID": opened.eventId });
    assert.deepEqual((await resumed.next()).kind, "tool_pre_execution");
    assert.deepEqual((await resumed.next()).taintState, "tainted");
    assert.deepEqual((await resumed.next()).kind, "tool_output_observed");
    assert.deepEqual((await resumed.next()).kind, "tool_finished");
    await resumed.close();
    assert.equal((await runtime.beforeTool(sink)).enforced, true);
    assert.equal((await get("/api/events/stream", { ...headers, "Last-Event-ID": opened.eventId })).status, 409);
    const history = await (await get("/api/runs/" + opened.runId + "/events")).json();
    assert.ok(responseContract("/api/runs/{runId}/events")(history));
    assert.equal(history.truncated, true);
    assert.deepEqual(history.events.map(event => event.sequence), [3, 4, 5, 6, 7]);
    assert.throws(() => api.publish({ ...opened, rawContent: "must never enter store" }), /unredacted/);
  } finally {
    await api.close();
  }
  assert.equal((await runtime.beforeTool({ ...sink, toolCallId: "after-portal-stop" })).reasonCode, "TAINTED_SIDE_EFFECT");
});

test("HTTP detector validates local results and enforces during malformed responses, timeout and process loss", async () => {
  const provenance = {
    modelId: "test", modelRevision: "fixed", probeHash: "a".repeat(64), featureExtractionHash: "b".repeat(64),
    layer: 9, precision: "fp32", provenanceType: "generation_forward_pass",
  };
  let identity;
  let responseMode = "ready";
  const service = createServer((req, res) => {
    if (req.headers.authorization !== headers.authorization) return res.writeHead(401).end();
    res.setHeader("content-type", "application/json");
    if (req.url === "/health") return res.end(JSON.stringify({ schemaVersion: 1, status: "ready" }));
    if (req.url === "/metadata") return res.end(JSON.stringify({ schemaVersion: 1, provenance, toolCalling: true, streaming: true }));
    assert.equal(req.url, "/v1/activations/inference?toolCallId=source");
    if (responseMode === "timeout") return;
    if (responseMode === "malformed") return res.end("{");
    return res.end(JSON.stringify({ ...identity, schemaVersion: 1, detectorMode: "direct_managed_qwen",
      status: "ready", provenance, score: 0.1, threshold: 0.5, latencyMs: 4, errorCode: null }));
  });
  service.listen(0, "127.0.0.1");
  await once(service, "listening");
  const origin = "http://127.0.0.1:" + service.address().port;
  assert.throws(() => createHttpDetector({ origin: "http://example.invalid", token }), /origin/);
  const detector = createHttpDetector({ origin, token, timeoutMs: 150, threshold: 0.5, provenance });
  const closed = async () => {
    const done = once(service, "close");
    service.close();
    service.closeAllConnections();
    await done;
  };
  const call = { sessionId: "one", toolName: "page", toolCallId: "source" };
  const action = (toolCallId) => ({ ...call, toolName: "sink", toolCallId });
  const events = [];
  const runtime = new ObservationRuntime(e => events.push(e), {
    mode: "enforce", detector, taintOnExposure: false, protectedTools: ["sink"], untrustedTools: ["page"],
  });
  try {
    assert.equal((await detector.health()).status, "ready");
    assert.equal((await detector.metadata()).provenance.probeHash, provenance.probeHash);
    runtime.observePrompt(call.sessionId, "task");
    await runtime.beforeTool(call);
    runtime.observeToolResult(call, { status: "completed", content: "page" });
    assert.equal(runtime.linkInference(call.sessionId, call.toolCallId, "inference"), true);
    identity = { runId: events[0].runId, sessionId: "one", toolCallId: "source", inferenceRequestId: "inference" };
    assert.equal((await runtime.beforeTool(action("healthy"))).verdict, "allow");
    responseMode = "malformed";
    assert.equal((await runtime.beforeTool(action("malformed"))).enforced, true);
    responseMode = "timeout";
    assert.equal((await runtime.beforeTool(action("slow"))).reasonCode, "DETECTOR_TIMEOUT");
  } finally {
    await closed();
  }
  assert.equal((await runtime.beforeTool(action("disconnected"))).reasonCode, "DETECTOR_TRANSPORT_ERROR");
});
