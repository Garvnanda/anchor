export default {
  id: "anchor.b1.tools",
  async setup(ctx) {
    const { appendFileSync } = await import("node:fs");
    const { join } = await import("node:path");
    const log = (event) => appendFileSync(join(ctx.location.directory, "tools.jsonl"), JSON.stringify(event) + "\n");
    await ctx.tool.transform(editor => {
      for (const tool of editor.list()) editor.remove(tool.id);
      for (const [name, color] of [["get_first_color", "blue"], ["get_second_color", "green"]]) {
        if (process.env.ANCHOR_B2_SINGLE === "1" && name === "get_second_color") continue;
        editor.add({ name, description: `Return the ${name === "get_first_color" ? "first" : "second"} color. Takes no arguments.`,
          input: { type: "object", properties: {}, additionalProperties: false },
          options: { codemode: false },
          execute: async (args) => {
            log({ executed: name, args });
            return { content: color };
          },
        });
      }
    });
    await ctx.tool.hook("execute.after", event => log({ tool: event.tool, id: event.id, status: event.status }));
  },
};
