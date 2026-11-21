import assert from "node:assert/strict";
import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { chromium } from "playwright-core";
const fixtures = JSON.parse(await readFile("dist/development-fixtures.json"));
const policy = fixtures[0],
  detector = fixtures[1],
  hash = "a".repeat(64);
const coverage = { openCodeVersion: "2.3.2", platform: "test", tools: [] };
const examples = {
  run_started: { taskFingerprint: hash },
  run_closed: { reasonCode: "DONE" },
  tool_pre_execution: { toolName: "example", actionClass: "read_only" },
  tool_output_observed: {
    toolName: "example",
    trust: "trusted",
    byteCount: 0,
    contentHash: hash,
    truncated: false,
  },
  taint_updated: { reasonCode: "OBSERVED" },
  tool_finished: { toolName: "example", status: "completed" },
  sink_verification: { count: 0, receiptHash: null },
  coverage_report: { report: coverage },
  error: { errorCode: "TEST" },
};
const events = [
  policy,
  detector,
  ...Object.entries(examples).map(([kind, details], i) => ({
    ...policy,
    kind,
    details,
    sequence: i + 3,
    eventId: "case-" + i,
  })),
];
let streams = 0;
const cursors = [];
const server = createServer(async (req, res) => {
  if (req.url.startsWith("/api/")) {
    if (req.headers.authorization !== "Bearer test") {
      res.writeHead(401).end();
      return;
    }
    if (req.url === "/api/events/stream") {
      streams++;
      cursors.push(req.headers["last-event-id"] ?? null);
      if (streams === 3) {
        res.writeHead(409).end();
        return;
      }
      res.writeHead(200, { "Content-Type": "text/event-stream" });
      res.flushHeaders();
      const row = { ...policy, eventId: "streamed", sequence: 12 };
      res.write("id: streamed\ndata: " + JSON.stringify(row) + "\n\n");
      if (streams <= 2) setTimeout(() => res.end(), 200);
      return;
    }
    const body =
      req.url === "/api/runs"
        ? { runs: [{ ...policy, state: "active" }] }
        : req.url === "/api/coverage"
          ? coverage
          : req.url.endsWith("/events")
            ? { truncated: false, events: events.toReversed() }
            : { schemaVersion: 1, status: "ready" };
    res.setHeader("Content-Type", "application/json");
    res.end(JSON.stringify(body));
    return;
  }
  const path =
    new URL(req.url, "http://localhost").pathname.slice(1) || "index.html";
  if (
    ![
      "index.html",
      "style.css",
      "app.js",
      "development-fixtures.json",
    ].includes(path)
  ) {
    res.writeHead(404).end();
    return;
  }
  res.setHeader(
    "Content-Type",
    path.endsWith(".js")
      ? "application/javascript"
      : path.endsWith(".css")
        ? "text/css"
        : path.endsWith(".json")
          ? "application/json"
          : "text/html",
  );
  res.end(await readFile("dist/" + path));
});
await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
const browser = await chromium.launch({
  executablePath:
    process.env.ANCHOR_BROWSER ??
    "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
  headless: true,
});
try {
  const page = await browser.newPage();
  const errors = [];
  page.on("pageerror", (err) => errors.push(err.message));
  const url = "http://127.0.0.1:" + server.address().port;
  await page.goto(url + "/?mode=fixture");
  await page.locator("details").nth(1).waitFor();
  assert.match(await page.locator("#status").innerText(), /synthetic/);
  if (process.env.ANCHOR_UI_PREVIEW)
    await page.screenshot({
      path: join(process.env.ANCHOR_UI_PREVIEW, "dashboard-desktop.png"),
    });
  await page.setViewportSize({ width: 375, height: 812 });
  assert.ok(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  );
  if (process.env.ANCHOR_UI_PREVIEW)
    await page.screenshot({
      path: join(process.env.ANCHOR_UI_PREVIEW, "dashboard-mobile.png"),
    });
  await page.goto(url);
  await page.getByLabel("Local bearer token").fill("invalid");
  await page.getByRole("button", { name: "Connect" }).click();
  await page.waitForFunction(() => document.querySelector("#status").textContent.includes("401"));
  await page.getByLabel("Local bearer token").fill("test");
  await page.getByRole("button", { name: "Connect" }).click();
  await page.waitForFunction(
    () => document.querySelectorAll("details").length === 12,
  );
  await page.waitForFunction(() => document.querySelector("#status").textContent.includes("Connected · history incomplete"));
  assert.deepEqual(cursors.slice(0,4),[null,"streamed","streamed",null]);
  assert.equal(await page.locator("details").count(), 12);
  await page.locator("summary").nth(1).focus();
  await page.keyboard.press("Enter");
  assert.ok(
    await page
      .locator("details")
      .nth(1)
      .evaluate((el) => el.open),
  );
  assert.deepEqual(errors, []);
  await page.addScriptTag({ path: 'node_modules/axe-core/axe.min.js' });
  const issues = await page.evaluate(async () => (await axe.run()).violations.map(issue => issue.id));
  assert.deepEqual(issues, [], 'Browser accessibility violations');
  console.log(
    "Verified all 11 event kinds, reconnect, duplicate suppression, mobile width and keyboard disclosure.",
  );
} finally {
  await browser.close();
  server.closeAllConnections();
  server.close();
}
