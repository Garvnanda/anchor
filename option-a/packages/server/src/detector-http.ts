import type { Detector, InferenceIdentity, Provenance } from "@anchor-ai/core";
import { contract, responseContract } from "./contracts.js";

const resultValid = contract("detector-result");
const healthValid = responseContract("/health");
const metadataValid = responseContract("/metadata");

export type HttpDetectorOptions = { origin: string; token: string; timeoutMs: number; threshold: number; provenance: Provenance };

async function limitedJson(response: Response): Promise<unknown> {
  if (!response.body) throw new Error("Empty detector response");
  const reader = response.body.getReader();
  const chunks: Uint8Array[] = [];
  let size = 0;
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > 65_536) {
        await reader.cancel();
        throw new Error("Oversize detector response");
      }
      chunks.push(value);
    }
    return JSON.parse(Buffer.concat(chunks).toString("utf8"));
  } finally {
    reader.releaseLock();
  }
}

export function createHttpDetector(options: HttpDetectorOptions): Detector & {
  health(): Promise<unknown>; metadata(): Promise<unknown>;
} {
  const origin = new URL(options.origin);
  if (origin.protocol !== "http:" || origin.hostname !== "127.0.0.1" || options.origin !== origin.origin) {
    throw new Error("Detector origin must be a bare HTTP origin on 127.0.0.1");
  }
  if (!/^[\x21-\x7e]{16,256}$/.test(options.token) || !Number.isSafeInteger(options.timeoutMs) ||
    options.timeoutMs < 1 || options.timeoutMs > 60_000) throw new Error("Invalid detector token or timeout");
  async function get(path: string, signal: AbortSignal, lookup?: InferenceIdentity): Promise<unknown> {
    const response = await fetch(new URL(path, origin), {
      headers: { authorization: "Bearer " + options.token }, redirect: "error", signal,
    });
    if (response.status === 404 && lookup) {
      await response.body?.cancel();
      return { ...lookup, schemaVersion: 1, detectorMode: "direct_managed_qwen", status: "unavailable",
        score: null, threshold: null, provenance: null, latencyMs: null, errorCode: "DETECTOR_UNAVAILABLE" };
    }
    if (!response.ok || !response.headers.get("content-type")?.startsWith("application/json")) {
      await response.body?.cancel();
      throw new Error("Detector returned an invalid HTTP response");
    }
    return limitedJson(response);
  }
  function verified(value: unknown, validate: (input: unknown) => boolean): unknown {
    if (!validate(value)) throw new Error("Detector response failed schema validation");
    return value;
  }
  return {
    provenance: { ...options.provenance }, threshold: options.threshold, timeoutMs: options.timeoutMs,
    async health() {
      return verified(await get("/health", AbortSignal.timeout(options.timeoutMs)), healthValid);
    },
    async metadata() {
      return verified(await get("/metadata", AbortSignal.timeout(options.timeoutMs)), metadataValid);
    },
    async lookup(identity, signal) {
      const path = "/v1/activations/" + encodeURIComponent(identity.inferenceRequestId) +
        "?toolCallId=" + encodeURIComponent(identity.toolCallId);
      return verified(await get(path, signal, identity), resultValid);
    },
  };
}
