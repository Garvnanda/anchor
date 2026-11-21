import { appendFileSync } from "node:fs";
import { isAbsolute } from "node:path";
import { ObservationRuntime } from "./dist/core/index.js";

export function createOpenClawAdapter(options, publish) {
  const runtime = new ObservationRuntime(publish, { ...options, source: "openclaw_plugin" });
  const session = ctx => ctx.sessionId ?? ctx.sessionKey ?? ctx.runId;
  const validId = value => typeof value === "string" && /^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$/.test(value);
  const call = (event, ctx) => ({
    sessionId: session(ctx), toolCallId: event.toolCallId ?? ctx.toolCallId, toolName: event.toolName,
  });
  return {
    register(api) {
      api.on("before_agent_run", (event, ctx) => runtime.observePrompt(session(ctx), event.prompt));
      api.on("before_prompt_build", (event, ctx) => runtime.observePrompt(session(ctx), event.prompt));
      api.on("before_tool_call", async (event, ctx) => {
        const current = call(event,ctx);
        if (options.mode === "enforce" && options.untrustedTools?.includes(event.toolName)
          && (!validId(current.sessionId) || !validId(current.toolCallId))) {
          return {block:true, blockReason:"ANCHOR_DENIED: UNCORRELATED_READ"};
        }
        // Some embedded runs begin outside the agent admission hook.
        // Start observation at a classified read while preserving denial on missing protected-call context.
        if (options.untrustedTools?.includes(event.toolName)) runtime.observePrompt(session(ctx), "");
        const decision = await runtime.beforeTool(current);
        if (decision.enforced) return { block: true, blockReason: "ANCHOR_DENIED: " + decision.reasonCode };
      });
      api.on("after_tool_call", (event, ctx) => {
        runtime.observeToolResult(call(event, ctx), event.error
          ? { status: "error" }
          : { status: "completed", content: JSON.stringify(event.result ?? null) });
      });
      if (options.markToolResults) {
        api.registerAgentToolResultMiddleware(event => {
          if (!options.untrustedTools?.includes(event.toolName) || event.isError) return;
          const content = event.result.content.map(part => part.type === "text"
            ? {...part,text:"[Anchor: untrusted tool result]\n" + part.text} : part);
          return {result:{...event.result,content}};
        }, {runtimes:["openclaw"]});
      }
      api.on("gateway_stop", () => runtime.close());
    },
    close: () => runtime.close(),
  };
}

export default {
  id: "anchor-ai",
  register(api) {
    const log = process.env.ANCHOR_OBSERVATION_LOG;
    if (!log || !isAbsolute(log)) throw Error("Set ANCHOR_OBSERVATION_LOG to an absolute file path");
    appendFileSync(log, "", { mode: 0o600 });
    createOpenClawAdapter({ mode: "monitor", ...api.pluginConfig }, event =>
      appendFileSync(log, JSON.stringify(event) + "\n")).register(api);
  },
};
