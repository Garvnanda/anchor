import { readFileSync } from "node:fs";
import { join } from "node:path";
import { timingSafeEqual } from "node:crypto";
import { createServer } from "node:http";
import type { ServerResponse } from "node:http";
import type { ObservationEvent } from "@anchor-ai/core";
import { contract } from "./contracts.js";

export * from "./detector-http.js";

type Run = Pick<ObservationEvent, "runId" | "sessionId" | "mode" | "detectorMode" | "taintState"> &
  { state: "active" | "closed"; sequence: number };
type Options = { dashboardDirectory?: string; token: string; port?: number; capacity?: number; coverage?: unknown };
const validEvent = contract("security-event");
const validCoverage = contract("coverage");

export async function createLocalServer(options: Options) {
  if (!/^[\x21-\x7e]{16,256}$/.test(options.token)) throw new Error("Invalid portal bearer token");
  const capacity = options.capacity ?? 1024;
  if (!Number.isSafeInteger(capacity) || capacity < 1 || capacity > 10_000) throw new Error("Invalid portal capacity");
  const coverage = structuredClone(options.coverage ?? { openCodeVersion: null, platform: process.platform, tools: [] });
  if (!validCoverage(coverage)) throw new Error("Invalid coverage report");
  const events: ObservationEvent[] = [];
  const runs = new Map<string, Run>();
  const clients = new Set<ServerResponse>();
  const bearer = Buffer.from("Bearer " + options.token);
  let closed = false;
  let origin = "";
  function json(response: ServerResponse, status: number, value: unknown) {
    response.writeHead(status, { "Content-Type": "application/json", "Cache-Control": "no-store" });
    response.end(JSON.stringify(value));
  }
  function frame(event: ObservationEvent): string {
    return "id: " + event.eventId + "\nevent: security_event\ndata: " + JSON.stringify(event) + "\n\n";
  }
  function send(response: ServerResponse, chunk: string): boolean {
    if (response.destroyed || !response.write(chunk)) {
      clients.delete(response);
      response.end();
      return false;
    }
    return true;
  }

  const server = createServer((request, response) => {
    const host = origin.slice("http://".length);
    if (request.headers.host !== host || (request.headers.origin !== undefined && request.headers.origin !== origin)) {
      return json(response, 403, { errorCode: "ORIGIN_OR_HOST_DENIED" });
    }
    if (request.method !== "GET" || !request.url?.startsWith("/") || request.url.startsWith("//")) {
      return json(response, 405, { errorCode: "METHOD_NOT_ALLOWED" });
    }
    const path = new URL(request.url, origin).pathname;
    const assets = new Map([["/", ["index.html", "text/html"]], ["/style.css", ["style.css", "text/css"]], ["/app.js", ["app.js", "text/javascript"]]]);
    const asset = assets.get(path);
    if (options.dashboardDirectory && asset?.[0]) {
      try {
        const bytes = readFileSync(join(options.dashboardDirectory, asset[0]));
        response.writeHead(200, { "Content-Type": asset[1] + "; charset=utf-8", "X-Content-Type-Options": "nosniff" });
        return response.end(bytes);
      } catch { return json(response, 404, { errorCode: "ASSET_UNAVAILABLE" }); }
    }
    const given = Buffer.from(request.headers.authorization ?? "");
    if (given.length !== bearer.length || !timingSafeEqual(given, bearer)) {
      return json(response, 401, { errorCode: "AUTH_REQUIRED" });
    }
    if (path === "/api/health") return json(response, 200, { schemaVersion: 1, status: "ready" });
    if (path === "/api/coverage") return json(response, 200, coverage);
    if (path === "/api/runs") return json(response, 200, {
      runs: [...runs.values()].map(({ sequence: _sequence, ...run }) => run),
    });
    const match = /^\/api\/runs\/([A-Za-z0-9_.:-]+)\/events$/.exec(path);
    if (match && match[1]) {
      const run = runs.get(match[1]);
      if (!run) return json(response, 404, { errorCode: "RUN_NOT_FOUND" });
      const items = events.filter(event => event.runId === run.runId);
      return json(response, 200, { events: items, truncated: items.length < run.sequence });
    }
    if (path === "/diagnostics") {
      response.writeHead(200, { "Content-Type": "text/plain; charset=utf-8", "Cache-Control": "no-store" });
      return response.end(`Anchor local event API\nRuns: ${runs.size}\nRetained events: ${events.length}\nSSE clients: ${clients.size}\n`);
    }
    if (path === "/api/events/stream") {
      const cursor = request.headers["last-event-id"];
      const index = cursor ? events.findIndex(event => event.eventId === cursor) : -1;
      if (cursor && index === -1) return json(response, 409, { errorCode: "CURSOR_EXPIRED" });
      if (clients.size >= 32) return json(response, 503, { errorCode: "STREAM_LIMIT" });
      response.writeHead(200, { "Content-Type": "text/event-stream", "Cache-Control": "no-store", Connection: "keep-alive" });
      response.flushHeaders();
      if (!send(response, ": connected\n\n")) return;
      for (const event of events.slice(index + 1)) if (!send(response, frame(event))) return;
      clients.add(response);
      response.on("close", () => clients.delete(response));
      return;
    }
    return json(response, 404, { errorCode: "NOT_FOUND" });
  });

  await new Promise<void>((resolve, reject) => {
    server.once("error", reject);
    server.listen(options.port ?? 0, "127.0.0.1", () => {
      server.removeListener("error", reject);
      resolve();
    });
  });
  const address = server.address();
  if (!address || typeof address === "string") throw new Error("No loopback listener");
  origin = "http://127.0.0.1:" + address.port;
  const heartbeat = setInterval(() => {
    for (const client of clients) send(client, ": heartbeat\n\n");
  }, 15_000);
  heartbeat.unref();

  return {
    origin,
    publish(value: ObservationEvent): void {
      if (closed) throw new Error("Event service closed");
      if (!validEvent(value)) throw new Error("Invalid or unredacted runtime event");
      const event = structuredClone(value);
      const previous = runs.get(event.runId);
      if ((previous && (previous.sequence >= event.sequence || previous.sessionId !== event.sessionId ||
        previous.state === "closed")) || events.some(item => item.eventId === event.eventId)) {
        throw new Error("Out-of-order or duplicate runtime event");
      }
      runs.delete(event.runId);
      runs.set(event.runId, { runId: event.runId, sessionId: event.sessionId, mode: event.mode,
        detectorMode: event.detectorMode, taintState: event.taintState, sequence: event.sequence,
        state: event.kind === "run_closed" ? "closed" : "active" });
      if (runs.size > capacity) {
        const oldest = runs.keys().next().value;
        if (oldest !== undefined) runs.delete(oldest);
      }
      events.push(event);
      if (events.length > capacity) events.shift();
      for (const client of clients) send(client, frame(event));
    },
    async close(): Promise<void> {
      if (closed) return;
      closed = true;
      clearInterval(heartbeat);
      for (const client of clients) client.end();
      clients.clear();
      await new Promise<void>((resolve, reject) => {
        server.close(error => error ? reject(error) : resolve());
        server.closeAllConnections();
      });
    },
  };
}
