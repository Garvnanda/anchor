export default {
  id: "anchor.profile.read-page",
  async setup(ctx) {
    const { appendFileSync } = await import("node:fs");
    const { join } = await import("node:path");
    const log = event => appendFileSync(join(ctx.location.directory,"tools.jsonl"), JSON.stringify(event)+"\n");
    await ctx.tool.transform(editor => {
      for (const tool of editor.list()) editor.remove(tool.id);
      editor.add({name:"read_page", description:"Read the local project bulletin.", input:{type:"object",properties:{},additionalProperties:false},
        options:{codemode:false}, execute:async args => {
          log({executed:"read_page",args});
          return {content:"The bulletin lists a blue sign at the library entrance."};
        }});
    });
    await ctx.tool.hook("execute.after", event => log({tool:event.tool,id:event.id,status:event.status}));
  }
};
