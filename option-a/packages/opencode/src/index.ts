import { appendFileSync } from "node:fs";
import { isAbsolute } from "node:path";
import { ObservationRuntime } from "@anchor-ai/core";
import { Plugin } from "@opencode/plugin";

const supportedVersion = "2.3.2";
const plugin = Plugin.define({
  id: "anchor.observe",
  async setup(ctx) {
    if (ctx.app.version !== supportedVersion) {
      throw new Error(`Anchor observation requires OpenCode ${supportedVersion}, got ${ctx.app.version}`);
    }
    const output = process.env.ANCHOR_OBSERVATION_LOG;
    if (!output || !isAbsolute(output)) {
      throw new Error("Set ANCHOR_OBSERVATION_LOG to an absolute path in an existing local directory");
    }
    appendFileSync(output, "", { mode: 0o600 });
    let reportedWriteError = false;
    const runtime = new ObservationRuntime(event => {
      try {
        appendFileSync(output, JSON.stringify(event) + "\n", { mode: 0o600 });
      } catch {
        if (!reportedWriteError) console.error("Anchor could not write observation events");
        reportedWriteError = true;
      }
    });
    await ctx.session.hook("prompt", event => {
      runtime.observePrompt(event.sessionID, event.prompt.text);
    });
    await ctx.tool.hook("execute.before", event => {
      runtime.observeToolCall({ sessionId: event.sessionID, toolCallId: event.id, toolName: event.tool });
    });
    await ctx.tool.hook("execute.after", event => {
      const call = { sessionId: event.sessionID, toolCallId: event.id, toolName: event.tool };
      if (event.status === "completed") {
        const content = event.result.content ?? event.result.output ?? null;
        runtime.observeToolResult(call, {
          status: "completed", content: typeof content === "string" ? content : JSON.stringify(content),
        });
      } else {
        runtime.observeToolResult(call, { status: "error" });
      }
    });
    return () => runtime.close();
  },
});

export default plugin;
