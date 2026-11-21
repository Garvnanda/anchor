import { appendFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";

export default {
  id: "anchor.audit",
  async setup(ctx) {
    const dir = ctx.location.directory;
    const log = (kind, fields = {}) =>
      appendFileSync(join(dir, "audit.jsonl"), JSON.stringify({ kind, ...fields }) + "\n");
    await ctx.session.hook("prompt", event => log("prompt", { sessionId: event.sessionID }));
    await ctx.tool.transform(editor => {
      for (const tool of editor.list()) editor.remove(tool.id);
      editor.add({
        name: "audit_sentinel",
        description: "Write the harmless local audit marker. Takes no arguments.",
        input: {
          type: "object", properties: {}, additionalProperties: false,
        },
        options: { codemode: false },
        execute: async () => {
          writeFileSync(join(dir, "sentinel"), "marker", { flag: "wx" });
          log("executed");
          return { content: "sentinel-created" };
        },
      });
    });
    const call = event => ({ tool: event.tool, sessionId: event.sessionID, callId: event.id });
    await ctx.tool.hook("execute.before", async event => {
      log("before", call(event));
      if (process.env.ANCHOR_AUDIT_DENY === "1" && event.tool === "audit_sentinel") {
        log("denied", call(event));
        throw new Error("ANCHOR_AUDIT_DENIED");
      }
    });
    await ctx.tool.hook("execute.after", event => {
      log("after", { ...call(event), status: event.status,
        markerResult: event.status === "completed" &&
          JSON.stringify(event.result.content).includes("sentinel-created") });
    });
    log("loaded", { version: ctx.app.version, bun: process.versions.bun ?? null });
  },
};
