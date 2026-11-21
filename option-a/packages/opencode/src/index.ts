import { appendFileSync } from "node:fs";
import { isAbsolute } from "node:path";
import { ObservationRuntime } from "@anchor-ai/core";
import type { Mode, ObservationEvent, PolicyOptions } from "@anchor-ai/core";
import { Plugin } from "@opencode/plugin";

const supportedVersion = "2.3.2";
export function createAnchorPlugin(options?: PolicyOptions, publish?: (event: ObservationEvent) => void) {
  return Plugin.define({ id: "anchor.observe", setup });

  async function setup(ctx: Plugin.Context) {
    if (ctx.app.version !== supportedVersion) {
      throw new Error(`Anchor observation requires OpenCode ${supportedVersion}, got ${ctx.app.version}`);
    }
    const output = process.env.ANCHOR_OBSERVATION_LOG;
    if (!publish && (!output || !isAbsolute(output))) {
      throw new Error("Set ANCHOR_OBSERVATION_LOG to an absolute path in an existing local directory");
    }
    if (!publish && output) appendFileSync(output, "", { mode: 0o600 });
    let reportedWriteError = false;
    const runtime = new ObservationRuntime(publish ?? (event => {
      try {
        if (output) appendFileSync(output, JSON.stringify(event) + "\n", { mode: 0o600 });
      } catch {
        if (!reportedWriteError) console.error("Anchor could not write observation events");
        reportedWriteError = true;
      }
    }), options ?? {
      mode: (process.env.ANCHOR_POLICY_MODE ?? "monitor") as Mode,
      isolatedDemo: process.env.ANCHOR_ISOLATED_DEMO === "1",
      protectedTools: process.env.ANCHOR_PROTECTED_TOOLS?.split(",") ?? [],
      untrustedTools: process.env.ANCHOR_UNTRUSTED_TOOLS?.split(",") ?? [],
    });
    await ctx.session.hook("prompt", event => {
      runtime.observePrompt(event.sessionID, event.prompt.text);
    });
    await ctx.tool.hook("execute.before", async event => {
      const decision = await runtime.beforeTool({ sessionId: event.sessionID, toolCallId: event.id, toolName: event.tool });
      if (decision.enforced) throw new Error("ANCHOR_DENIED: " + decision.reasonCode);
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
  }
}

export default createAnchorPlugin();
