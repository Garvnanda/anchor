export function visibleDetails(event) {
  if (event.kind !== "detector_result") return event.details;
  const d = event.details;
  const correlated = [
    "runId",
    "sessionId",
    "toolCallId",
    "inferenceRequestId",
  ].every((k) => event[k] && event[k] === d[k]);
  if (
    !correlated ||
    d.status !== "ready" ||
    d.provenance?.provenanceType !== "generation_forward_pass"
  )
    return {
      status: d.status,
      score: null,
      reason: correlated
        ? (d.errorCode ?? "Direct provenance unavailable")
        : "Correlation mismatch",
    };
  return d;
}
export function timeline(events, run) {
  return [...events.values()]
    .filter((e) => !run || run === e.runId)
    .sort((a, b) => a.runId.localeCompare(b.runId) || a.sequence - b.sequence);
}
export async function* frames(body) {
  const reader = body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";
  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) return;
      buffer += value;
      let match;
      while ((match = /\r?\n\r?\n/.exec(buffer))) {
        const lines = buffer.slice(0, match.index).split(/\r?\n/);
        buffer = buffer.slice(match.index + match[0].length);
        const data = lines
          .filter((l) => l.startsWith("data:"))
          .map((l) => l.slice(5).trimStart())
          .join("\n");
        if (data)
          yield {
            data: JSON.parse(data),
            id: lines
              .find((l) => l.startsWith("id:"))
              ?.slice(3)
              .trim(),
          };
      }
    }
  } finally {
    reader.releaseLock();
  }
}
