import { createHmac, randomBytes, randomUUID } from "node:crypto";
import { Buffer } from "node:buffer";
import { readEvidence } from "./detector.js";
import type { Detector, DetectorResult, InferenceIdentity } from "./detector.js";

export * from "./detector.js";
export type Mode = "off" | "monitor" | "enforce";
export type PolicyOptions = {
  mode?: Mode;
  isolatedDemo?: boolean;
  protectedTools?: readonly string[];
  untrustedTools?: readonly string[];
  taintOnExposure?: boolean;
  detector?: Detector;
};
export type Decision = { verdict: "allow" | "block"; reasonCode: string; enforced: boolean };
export type Call = { sessionId: string; toolCallId: string; toolName: string };

type EventDetails =
  | { kind: "run_started"; details: { taskFingerprint: string } }
  | { kind: "run_closed"; details: { reasonCode: string } }
  | { kind: "taint_updated"; details: { reasonCode: string } }
  | { kind: "tool_pre_execution"; toolCallId: string; details: { toolName: string; actionClass: "unknown" | "side_effect" | "read_only" } }
  | { kind: "policy_decision"; toolCallId: string; details: { toolName: string } & Decision }
  | { kind: "detector_result"; toolCallId: string; inferenceRequestId: string; details: DetectorResult }
  | { kind: "tool_output_observed"; toolCallId: string; details: {
      toolName: string; trust: "unknown" | "untrusted"; byteCount: number; contentHash: string; truncated: boolean;
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
  mode: Mode;
  detectorMode: "policy_only" | "direct_managed_qwen";
  taintState: "clean" | "tainted";
  redacted: true;
}>;

type Run = {
  id: string; sequence: number; tainted: boolean; generation: number;
  pending: Set<string>; exposures: Map<string, string | null>; checked: Set<string>;
};
const maxSessions = 256;
const maxInspectionBytes = 250_000;
const wireId = /^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$/;

export class ObservationRuntime {
  readonly #runs = new Map<string, Run>();
  readonly #fingerprintKey = randomBytes(32);
  readonly #mode: Mode;
  readonly #protected: Set<string>;
  readonly #untrusted: Set<string>;
  readonly #taintOnExposure: boolean;
  readonly #detector: Detector | undefined;
  readonly #publish: (event: ObservationEvent) => void;

  constructor(publish: (event: ObservationEvent) => void, options: PolicyOptions = {}) {
    this.#publish = publish;
    this.#mode = options.mode ?? "monitor";
    if (!["off", "monitor", "enforce"].includes(this.#mode)) throw new Error("Invalid Anchor mode");
    if (this.#mode === "off" && options.isolatedDemo !== true) throw new Error("OFF requires an isolated demo");
    this.#protected = new Set(options.protectedTools);
    this.#untrusted = new Set(options.untrustedTools);
    for (const tool of [...this.#protected, ...this.#untrusted]) {
      if (!wireId.test(tool) || (this.#protected.has(tool) && this.#untrusted.has(tool))) {
        throw new Error("Invalid or overlapping Anchor tool classification");
      }
    }
    if (options.detector && (!Number.isSafeInteger(options.detector.timeoutMs) || options.detector.timeoutMs < 1 ||
        options.detector.timeoutMs > 60_000 || !Number.isFinite(options.detector.threshold) ||
        options.detector.threshold < 0 || options.detector.threshold > 1 ||
        options.detector.provenance.provenanceType !== "generation_forward_pass")) throw new Error("Invalid detector configuration");
    if (options.taintOnExposure === false && !options.detector) throw new Error("Disabling exposure taint requires a detector");
    this.#taintOnExposure = options.taintOnExposure ?? true;
    this.#detector = options.detector;
  }

  observePrompt(sessionId: string, text: string): void {
    if (!wireId.test(sessionId) || this.#runs.has(sessionId)) return;
    if (this.#runs.size >= maxSessions) return;
    const run: Run = {
      id: randomUUID(), sequence: 0, tainted: false, generation: 0,
      pending: new Set(), exposures: new Map(), checked: new Set(),
    };
    this.#runs.set(sessionId, run);
    this.#emit(sessionId, run, { kind: "run_started", details: { taskFingerprint: this.#fingerprint(text) } });
  }

  observeToolCall(call: Call): void {
    const run = this.#callRun(call);
    if (!run) return;
    const untrusted = this.#untrusted.has(call.toolName);
    if (untrusted) {
      run.generation++;
      if (run.pending.size >= 256 || run.pending.has(call.toolCallId)) this.#taint(call.sessionId, run, "EXPOSURE_LIMIT");
      else run.pending.add(call.toolCallId);
    }
    this.#emit(call.sessionId, run, {
      kind: "tool_pre_execution", toolCallId: call.toolCallId,
      details: { toolName: call.toolName, actionClass: this.#protected.has(call.toolName) ? "side_effect" :
        untrusted ? "read_only" : "unknown" },
    });
  }

  observeToolResult(call: Call, result: { status: "completed"; content: string } | { status: "error" }): void {
    const run = this.#callRun(call);
    if (!run) return;
    const untrusted = this.#untrusted.has(call.toolName);
    if (untrusted) {
      run.generation++;
      run.pending.delete(call.toolCallId);
    }
    if (result.status === "completed") {
      const byteCount = Buffer.byteLength(result.content);
      if (untrusted) {
        if (this.#detector) {
          if (run.exposures.size >= 64 || run.exposures.has(call.toolCallId)) this.#taint(call.sessionId, run, "EXPOSURE_LIMIT");
          else run.exposures.set(call.toolCallId, null);
        }
        if (this.#taintOnExposure) this.#taint(call.sessionId, run, "UNTRUSTED_EXPOSURE");
      }
      this.#emit(call.sessionId, run, {
        kind: "tool_output_observed", toolCallId: call.toolCallId,
        details: {
          toolName: call.toolName, trust: untrusted ? "untrusted" : "unknown", byteCount,
          contentHash: this.#fingerprint(result.content), truncated: byteCount > maxInspectionBytes,
        },
      });
    }
    this.#emit(call.sessionId, run, {
      kind: "tool_finished", toolCallId: call.toolCallId,
      details: { toolName: call.toolName, status: result.status },
    });
  }

  linkInference(sessionId: string, toolCallId: string, inferenceRequestId: string): boolean {
    const run = this.#runs.get(sessionId);
    if (!wireId.test(inferenceRequestId) || !run || run.exposures.get(toolCallId) !== null) return false;
    run.exposures.set(toolCallId, inferenceRequestId);
    run.generation++;
    return true;
  }

  async beforeTool(call: Call): Promise<Decision> {
    this.observeToolCall(call);
    if (!this.#protected.has(call.toolName)) return { verdict: "allow", reasonCode: "OUTSIDE_PROTECTED_SCOPE", enforced: false };
    const run = this.#callRun(call);
    let reason = "CLEAN_RUN";
    if (!run) reason = "MISSING_RUN";
    else if (run.checked.has(call.toolCallId) || run.checked.size >= 4096) reason = "CALL_ALREADY_CHECKED_OR_LIMIT";
    else {
      run.checked.add(call.toolCallId);
      if (run.tainted) reason = "TAINTED_SIDE_EFFECT";
      else if (run.pending.size) reason = "PENDING_TOOL_OUTPUT";
      else if (this.#detector && this.#mode !== "off") reason = await this.#checkEvidence(call.sessionId, run, this.#detector);
    }
    const verdict = reason === "CLEAN_RUN" ? "allow" : "block";
    const decision: Decision = { verdict, reasonCode: reason, enforced: verdict === "block" && this.#mode === "enforce" };
    if (run) this.#emit(call.sessionId, run, {
      kind: "policy_decision", toolCallId: call.toolCallId, details: { toolName: call.toolName, ...decision },
    });
    return decision;
  }

  async #checkEvidence(sessionId: string, run: Run, detector: Detector): Promise<string> {
    const version = run.generation;
    const deadline = performance.now() + detector.timeoutMs;
    for (const [toolCallId, inferenceRequestId] of run.exposures) {
      if (!inferenceRequestId) return "DETECTOR_UNCORRELATED";
      const identity: InferenceIdentity = { runId: run.id, sessionId, toolCallId, inferenceRequestId };
      const remaining = Math.ceil(deadline - performance.now());
      if (remaining < 1) return "DETECTOR_TIMEOUT";
      const result = await readEvidence(detector, identity, remaining);
      if (this.#runs.get(sessionId) !== run || run.generation !== version || run.tainted || run.pending.size) {
        return "STATE_CHANGED_DURING_SCORE";
      }
      this.#emit(sessionId, run, { kind: "detector_result", toolCallId, inferenceRequestId, details: result });
      if (result.status !== "ready" || result.score === null) return result.errorCode ?? "DETECTOR_UNAVAILABLE";
      if (result.score >= detector.threshold) {
        this.#taint(sessionId, run, "DETECTOR_THRESHOLD");
        return "DETECTOR_THRESHOLD";
      }
    }
    return "CLEAN_RUN";
  }

  close(): void {
    for (const [sessionId, run] of this.#runs) {
      this.#runs.delete(sessionId);
      this.#emit(sessionId, run, { kind: "run_closed", details: { reasonCode: "PLUGIN_UNLOAD" } });
    }
  }

  #callRun(call: Call): Run | undefined {
    if (!wireId.test(call.toolCallId) || !wireId.test(call.toolName)) return;
    return this.#runs.get(call.sessionId);
  }

  #taint(sessionId: string, run: Run, reasonCode: string): void {
    if (run.tainted) return;
    run.tainted = true;
    this.#emit(sessionId, run, { kind: "taint_updated", details: { reasonCode } });
  }

  #fingerprint(text: string): string {
    const sample = Buffer.from(text.slice(0, maxInspectionBytes + 1)).subarray(0, maxInspectionBytes);
    return createHmac("sha256", this.#fingerprintKey).update(sample).digest("hex");
  }

  #emit(sessionId: string, run: Run, event: EventDetails): void {
    try {
      this.#publish({
        schemaVersion: 1, eventId: randomUUID(), runId: run.id, sessionId, sequence: ++run.sequence,
        timestamp: new Date().toISOString(), source: "opencode_plugin", mode: this.#mode,
        detectorMode: this.#detector ? "direct_managed_qwen" : "policy_only",
        taintState: run.tainted ? "tainted" : "clean", redacted: true, ...event,
      });
    } catch {
      // Observers are outside the authorization path.
    }
  }
}
