export type InferenceIdentity = { runId: string; sessionId: string; toolCallId: string; inferenceRequestId: string };
export type Provenance = {
  modelId: string; modelRevision: string; probeHash: string; featureExtractionHash: string;
  precision: string; layer: number; provenanceType: "generation_forward_pass" | "auxiliary_forward_pass";
};
export type DetectorResult = InferenceIdentity & {
  schemaVersion: 1; detectorMode: "direct_managed_qwen";
  status: "ready" | "unavailable" | "incompatible" | "error" | "timeout";
  score: number | null; threshold: number | null; latencyMs: number | null;
  provenance: Provenance | null; errorCode: string | null;
};
export type Detector = {
  timeoutMs: number; threshold: number; provenance: Provenance;
  lookup(identity: InferenceIdentity, signal: AbortSignal): Promise<unknown>;
};

export async function readEvidence(detector: Detector, identity: InferenceIdentity, timeout: number): Promise<DetectorResult> {
  const started = performance.now();
  const controller = new AbortController();
  const base = { ...identity, schemaVersion: 1, detectorMode: "direct_managed_qwen" } as const;
  function failed(status: Exclude<DetectorResult["status"], "ready">, errorCode: string): DetectorResult {
    return { ...base, status, errorCode, score: null, threshold: null, provenance: null, latencyMs: performance.now() - started };
  }
  let timer: ReturnType<typeof setTimeout> | undefined;
  try {
    const deadline = new Promise<never>((_, reject) => {
      timer = setTimeout(() => {
        controller.abort();
        reject(new Error("detector timeout"));
      }, timeout);
    });
    const raw = await Promise.race([detector.lookup(identity, controller.signal), deadline]);
    if (performance.now() - started >= timeout) return failed("timeout", "DETECTOR_TIMEOUT");
    if (typeof raw !== "object" || !raw) return failed("error", "DETECTOR_MALFORMED");
    const response = raw as Partial<DetectorResult>;
    if (response.schemaVersion !== 1 || response.detectorMode !== "direct_managed_qwen" ||
      response.runId !== identity.runId || response.sessionId !== identity.sessionId ||
      response.toolCallId !== identity.toolCallId || response.inferenceRequestId !== identity.inferenceRequestId) {
      return failed("incompatible", "DETECTOR_IDENTITY_MISMATCH");
    }
    switch (response.status) {
      case "unavailable": return failed("unavailable", "DETECTOR_UNAVAILABLE");
      case "incompatible": return failed("incompatible", "DETECTOR_INCOMPATIBLE");
      case "timeout": return failed("timeout", "DETECTOR_TIMEOUT");
      case "error": return failed("error", "DETECTOR_ERROR");
      case "ready": break;
      default: return failed("error", "DETECTOR_MALFORMED");
    }
    const { modelId, modelRevision, probeHash, featureExtractionHash, layer, precision, provenanceType } = detector.provenance;
    const pin = { modelId, modelRevision, probeHash, featureExtractionHash, layer, precision, provenanceType };
    const provenance = response.provenance;
    if (!provenance || Object.entries(pin).some(([key, value]) => provenance[key as keyof Provenance] !== value) ||
      response.threshold !== detector.threshold) return failed("incompatible", "DETECTOR_PROVENANCE_MISMATCH");
    if (typeof response.score !== "number" || !Number.isFinite(response.score) || response.score < 0 || response.score > 1 ||
      typeof response.latencyMs !== "number" || !Number.isFinite(response.latencyMs) || response.latencyMs < 0 ||
      response.errorCode !== null) return failed("error", "DETECTOR_MALFORMED");
    return { ...base, status: "ready", score: response.score, threshold: detector.threshold,
      latencyMs: response.latencyMs, provenance: pin, errorCode: null };
  } catch {
    return controller.signal.aborted ? failed("timeout", "DETECTOR_TIMEOUT") : failed("error", "DETECTOR_TRANSPORT_ERROR");
  } finally {
    clearTimeout(timer);
  }
}
