import { open } from "node:fs/promises";
import { setTimeout } from "node:timers/promises";
import { StringDecoder } from "node:string_decoder";

// Follow one append-only JSONL file per host invocation. A torn last record
// stays buffered until the writer finishes it.
export async function follow(path, publish, signal) {
  const file = await open(path, "r");
  const decoder = new StringDecoder("utf8");
  let offset = 0, pending = "";
  const bytes = Buffer.alloc(65536);
  try {
    while (!signal.aborted) {
      const {bytesRead} = await file.read(bytes, 0, bytes.length, offset);
      if (!bytesRead) {
        await setTimeout(200);
        continue;
      }
      offset += bytesRead;
      const lines = (pending + decoder.write(bytes.subarray(0, bytesRead))).split("\n");
      pending = lines.pop();
      if (pending.length > 262144) throw Error("Event exceeds audit record limit");
      for (const line of lines) if (line.trim()) publish(JSON.parse(line));
    }
  } finally { await file.close(); }
}
