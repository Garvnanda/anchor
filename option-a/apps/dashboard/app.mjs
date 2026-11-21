import validators from "./dist/validate.cjs";
import { visibleDetails, timeline, frames } from "./model.mjs";
const $ = (s) => document.querySelector(s);
const events = new Map(),
  runs = new Map();
let controller,
  coverage,
  partial = false;
function add(event) {
  if (!validators.validateEvent(event)) throw Error("Invalid event received");
  if (!events.has(event.eventId)) events.set(event.eventId, event);
  const r = runs.get(event.runId);
  if (!r || event.sequence > (r.sequence ?? 0))
    runs.set(event.runId, {
      ...r,
      ...event,
      state:
        event.kind === "run_closed"
          ? "closed"
          : event.kind === "run_started"
            ? "active"
            : (r?.state ?? "state unreported"),
    });
  if (event.kind === "coverage_report") coverage = event.details.report;
}
function render() {
  const filter = $("#filter"),
    selected = filter.value;
  filter.replaceChildren(new Option("All runs", ""));
  $("#runs").replaceChildren();
  for (const r of runs.values()) {
    filter.add(new Option(r.runId, r.runId));
    const p = document.createElement("p");
    p.textContent = [
      r.runId,
      r.sessionId,
      r.source,
      r.mode,
      r.detectorMode,
      r.taintState,
      r.state,
    ].join(" · ");
    $("#runs").append(p);
  }
  if (runs.has(selected)) filter.value = selected;
  if (!runs.size) $("#runs").textContent = "No runs available.";
  const list = $("#timeline");
  list.replaceChildren();
  const last = new Map();
  for (const e of timeline(events, filter.value)) {
    const row = document.createElement("details"),
      title = document.createElement("summary"),
      body = document.createElement("pre");
    const gap = e.sequence !== (last.get(e.runId) ?? 0) + 1;
    last.set(e.runId, e.sequence);
    title.textContent =
      (gap ? "Sequence gap · " : "") +
      "#" +
      e.sequence +
      " · " +
      e.kind.replaceAll("_", " ") +
      " · " +
      e.runId;
    body.textContent = JSON.stringify(
      {
        timestamp: e.timestamp,
        source: e.source,
        sessionId: e.sessionId,
        toolCallId: e.toolCallId,
        inferenceRequestId: e.inferenceRequestId,
        ...visibleDetails(e),
      },
      null,
      2,
    );
    row.append(title, body);
    list.append(row);
  }
  if (!list.childElementCount) list.textContent = "No recorded events.";
  if (coverage) $("#coverage").textContent = JSON.stringify(coverage, null, 2);
}
$("#filter").onchange = render;
render();
const local = ["localhost", "127.0.0.1", "[::1]"].includes(location.hostname);
const fixture =
  local && new URLSearchParams(location.search).get("mode") === "fixture";
if (fixture) {
  $("form").hidden = true;
  $("form").style.display = "none";
  $("#status").textContent = "Development fixtures · synthetic events";
  fetch("development-fixtures.json")
    .then((r) => r.json())
    .then((rows) => {
      rows.forEach(add);
      render();
    })
    .catch(
      () => ($("#status").textContent = "Development fixtures unavailable"),
    );
}
$("form").onsubmit = async (event) => {
  event.preventDefault();
  if (!local || fixture) return;
  controller?.abort();
  controller = new AbortController();
  const { signal } = controller;
  const headers = { Authorization: "Bearer " + $("input").value };
  $("input").value = "";
  let cursor;
  partial = false;
  async function request(path, extra = {}) {
    const response = await fetch(path, {
      headers: { ...headers, ...extra },
      signal,
      cache: "no-store",
      redirect: "error",
    });
    if (!response.ok)
      throw Object.assign(Error("HTTP " + response.status), {
        status: response.status,
      });
    return response;
  }
  while (!signal.aborted) {
    let stream;
    try {
      if (!cursor) {
        events.clear();
        runs.clear();
        coverage = null;
        $("#coverage").textContent = "Awaiting coverage report.";
        render();
        $("#status").textContent = "Loading local run history…";
        const json = async (path) => (await request(path)).json();
        const [health, report] = await Promise.all(
          ["/api/health", "/api/coverage"].map(json),
        );
        if (health.status !== "ready" || !validators.validateCoverage(report))
          throw Error("Portal unavailable or invalid coverage");
        coverage = report;
        // Subscribe before reading snapshots so events emitted during retrieval remain buffered.
        stream = await request("/api/events/stream", {
          Accept: "text/event-stream",
        });
        const history = await json("/api/runs");
        for (const r of history.runs) {
          runs.set(r.runId, r);
          const snapshot = await json(
            "/api/runs/" + encodeURIComponent(r.runId) + "/events",
          );
          partial ||= snapshot.truncated;
          snapshot.events.forEach(add);
        }
      } else
        stream = await request("/api/events/stream", {
          Accept: "text/event-stream",
          "Last-Event-ID": cursor,
        });
      render();
      $("#status").textContent = partial
        ? "Connected · history incomplete"
        : "Connected · local runtime";
      for await (const frame of frames(stream.body)) {
        if (frame.id !== frame.data.eventId)
          throw Error("Event identity mismatch");
        add(frame.data);
        cursor = frame.id;
        render();
      }
      throw Error("Stream ended");
    } catch (error) {
      if (stream?.body && !stream.body.locked)
        await stream.body.cancel().catch(() => {});
      if (signal.aborted) return;
      if (error.status === 409) {
        cursor = null;
        partial = true;
      }
      $("#status").textContent = "Disconnected · " + error.message;
      if ([401, 403, 404].includes(error.status)) return;
      await new Promise((resolve) => setTimeout(resolve, 2000));
    }
  }
};
