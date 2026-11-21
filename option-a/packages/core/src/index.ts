import { createHmac, randomBytes, randomUUID } from "node:crypto";
import { Buffer } from "node:buffer";

type EventDetails =
  | { kind: "run_started"; details: { taskFingerprint: string } }
  | { kind: "run_closed"; details: { reasonCode: "SESSION_LIMIT" | "PLUGIN_UNLOAD" } }
  | { kind: "tool_pre_execution"; toolCallId: string; details: { toolName: string; actionClass: "unknown" } }
  | { kind: "tool_output_observed"; toolCallId: string; details: {
      toolName: string; trust: "unknown"; byteCount: number; contentHash: string; truncated: boolean;
    } }
  | { kind: "tool_finished"; toolCallId: string; details: { toolName: string; status: "completed" | "error" } };

export type ObservationEvent = Readonly<EventDetails & {
  schemaVersion: 1;
  eventId: string;
  runId: string;
  sessionId: string;
  sequence: number;
  timestamp: string;
  source: "opencode_plugin";
  mode: "monitor";
  detectorMode: "policy_only";
  taintState: "clean";
  redacted: true;
}>;

type Run = { id: string; sequence: number };
type Call = { sessionId: string; toolCallId: string; toolName: string };
const maxSessions = 256;
const maxInspectionBytes = 250_000;
const wireId = /^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$/;

export class ObservationRuntime {
  readonly #runs = new Map<string, Run>();
  readonly #fingerprintKey = randomBytes(32);
  readonly #publish: (event: ObservationEvent) => void;

  constructor(publish: (event: ObservationEvent) => void) {
    this.#publish = publish;
  }

  observePrompt(sessionId: string, text: string): void {
    if (!wireId.test(sessionId) || this.#findRun(sessionId)) return;
    if (this.#runs.size >= maxSessions) {
      const oldest = this.#runs.entries().next().value;
      if (oldest) {
        this.#runs.delete(oldest[0]);
        this.#emit(oldest[0], oldest[1], { kind: "run_closed", details: { reasonCode: "SESSION_LIMIT" } });
      }
    }
    const run = { id: randomUUID(), sequence: 0 };
    this.#runs.set(sessionId, run);
    this.#emit(sessionId, run, { kind: "run_started", details: { taskFingerprint: this.#fingerprint(text) } });
  }

  observeToolCall(call: Call): void {
    const run = this.#callRun(call);
    if (!run) return;
    this.#emit(call.sessionId, run, {
      kind: "tool_pre_execution", toolCallId: call.toolCallId,
      details: { toolName: call.toolName, actionClass: "unknown" },
    });
  }

  observeToolResult(call: Call, result: { status: "completed"; content: string } | { status: "error" }): void {
    const run = this.#callRun(call);
    if (!run) return;
    if (result.status === "completed") {
      const byteCount = Buffer.byteLength(result.content);
      this.#emit(call.sessionId, run, {
        kind: "tool_output_observed", toolCallId: call.toolCallId,
        details: {
          toolName: call.toolName, trust: "unknown", byteCount,
          contentHash: this.#fingerprint(result.content), truncated: byteCount > maxInspectionBytes,
        },
      });
    }
    this.#emit(call.sessionId, run, {
      kind: "tool_finished", toolCallId: call.toolCallId,
      details: { toolName: call.toolName, status: result.status },
    });
  }

  close(): void {
    for (const [sessionId, run] of this.#runs) {
      this.#runs.delete(sessionId);
      this.#emit(sessionId, run, { kind: "run_closed", details: { reasonCode: "PLUGIN_UNLOAD" } });
    }
  }

  #callRun(call: Call): Run | undefined {
    if (!wireId.test(call.toolCallId) || !wireId.test(call.toolName)) return;
    return this.#findRun(call.sessionId);
  }

  #findRun(sessionId: string): Run | undefined {
    const run = this.#runs.get(sessionId);
    if (run) {
      this.#runs.delete(sessionId);
      this.#runs.set(sessionId, run);
    }
    return run;
  }

  #fingerprint(text: string): string {
    const sample = Buffer.from(text.slice(0, maxInspectionBytes + 1)).subarray(0, maxInspectionBytes);
    return createHmac("sha256", this.#fingerprintKey).update(sample).digest("hex");
  }

  #emit(sessionId: string, run: Run, event: EventDetails): void {
    this.#publish({
      schemaVersion: 1, eventId: randomUUID(), runId: run.id, sessionId, sequence: ++run.sequence,
      timestamp: new Date().toISOString(), source: "opencode_plugin", mode: "monitor",
      detectorMode: "policy_only", taintState: "clean", redacted: true, ...event,
    });
  }
}
