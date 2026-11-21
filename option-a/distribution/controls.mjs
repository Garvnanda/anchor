import { readFileSync } from "node:fs";
import { spawn } from "node:child_process";
import { randomUUID } from "node:crypto";
import { createInterface } from "node:readline";
import { once } from "node:events";
import { ObservationRuntime } from "./dist/core/index.js";

// One worker owns one model and consumes one explicitly identified control at a time.
export async function runControls(script, publish) {
  const child = spawn(process.env.ANCHOR_PYTHON || "python", [script, "--wire"], {stdio:["pipe","pipe","inherit"]});
  const completed = once(child, "close");
  const replies = createInterface({input:child.stdout})[Symbol.asyncIterator]();
  try {
    const controls = JSON.parse(readFileSync(new URL("./dist/python/controls.json", import.meta.url),"utf8"));
    for (const {id, label, task, output} of controls) {
      const sessionId = "matched-profile-" + label;
      const toolCallId = randomUUID(), inferenceRequestId = randomUUID();
      let runId, result;
      const header = await replies.next();
      if (header.done) throw Error("Qwen stopped before the control");
      const {threshold, provenance} = JSON.parse(header.value);
      const runtime = new ObservationRuntime(event => {
        runId = event.runId;
        publish(event);
      }, {source:"managed_demo", mode:"enforce", protectedTools:["submit_receipt"], untrustedTools:["read_page"],
        taintOnExposure:false, detector:{timeoutMs:3000, threshold, provenance, lookup:async () => result}});
      try {
        runtime.observePrompt(sessionId, task);
        const read = {sessionId, toolName:"read_page", toolCallId};
        await runtime.beforeTool(read);
        runtime.observeToolResult(read, {status:"completed",content:output});
        if (!runtime.linkInference(sessionId,toolCallId,inferenceRequestId)) throw Error("Could not link generation");
        child.stdin.write(JSON.stringify({runId,sessionId,toolCallId,inferenceRequestId}) + "\n");
        const reply = await replies.next();
        if (reply.done) throw Error("Missing generation result");
        const {control, evidence} = JSON.parse(reply.value);
        if (control !== id) throw Error("Unexpected control identity");
        result = evidence;
        const decision = await runtime.beforeTool({sessionId, toolName:"submit_receipt",toolCallId:randomUUID()});
        const receipts = [];
        if (!decision.enforced) receipts.push(control);
        console.log(JSON.stringify({control, score:result.score, threshold, reason:decision.reasonCode, receipts:receipts.length}));
        if (decision.reasonCode !== (label ? "DETECTOR_THRESHOLD" : "CLEAN_RUN")) throw Error("Control failed");
      } finally { runtime.close(); }
    }
    child.stdin.end();
    if ((await completed)[0] !== 0) throw Error("Qwen worker failed");
  } finally { child.kill(); }
}
