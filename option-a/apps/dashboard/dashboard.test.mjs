import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { visibleDetails, timeline, frames } from "./model.mjs";
const fixtures = JSON.parse(
  readFileSync(
    new URL("../../../contracts/fixtures/cases.json", import.meta.url),
  ),
);
const event = fixtures.find(
  (c) => c.valid && c.data.kind === "detector_result",
).data;
test("only correlated direct scores are visible", () => {
  assert.equal(visibleDetails(event).score, 0.6);
  assert.equal(
    visibleDetails({ ...event, toolCallId: "different" }).score,
    null,
  );
  assert.equal(
    visibleDetails({
      ...event,
      details: { ...event.details, status: "timeout" },
    }).score,
    null,
  );
});
test("late events sort by run sequence", () =>
  assert.deepEqual(
    timeline(
      new Map([
        [2, { runId: "r", sequence: 2 }],
        [1, { runId: "r", sequence: 1 }],
      ]),
      "r",
    ).map((e) => e.sequence),
    [1, 2],
  ));
test("split SSE records and comments", async () => {
  const stream = new ReadableStream({
    start(c) {
      for (const s of [":beat\n\nid: e\r\n", 'data: {"n":1}\r', "\n\r\n"])
        c.enqueue(new TextEncoder().encode(s));
      c.close();
    },
  });
  const records = [];
  for await (const frame of frames(stream)) records.push(frame);
  assert.deepEqual(records, [{ id: "e", data: { n: 1 } }]);
});
