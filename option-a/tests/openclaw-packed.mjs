import assert from "node:assert/strict";
import { test } from "node:test";
import { createOpenClawAdapter } from "../distribution/openclaw.mjs";

test("OpenClaw embedded tool hooks retain taint, deny uncorrelated reads and isolate sessions", async () => {
  const hooks = new Map(), events = [];
  const adapter = createOpenClawAdapter({mode:"enforce",untrustedTools:["read"],protectedTools:["write"],
    markToolResults:true}, event => events.push(event));
  let middleware;
  adapter.register({on:(name, handler) => hooks.set(name, handler),registerAgentToolResultMiddleware:handler => { middleware = handler; }});
  const ctx = {sessionId:"embedded"};
  const read = {toolName:"read", toolCallId:"read-1"};
  assert.equal((await hooks.get("before_tool_call")({toolName:"read"},ctx)).block,true);
  assert.equal(await hooks.get("before_tool_call")(read,ctx),undefined);
  hooks.get("after_tool_call")({...read,result:"fixture"},ctx);
  const write = {toolName:"write",toolCallId:"write-1"};
  const decision = await hooks.get("before_tool_call")(write,ctx);
  assert.match(decision.blockReason,/TAINTED_SIDE_EFFECT/);
  hooks.get("before_agent_run")({prompt:"Fresh task"},{sessionId:"other"});
  assert.equal(await hooks.get("before_tool_call")(write,{sessionId:"other"}),undefined);
  const result = {content:[{type:"text",text:"fixture"}]};
  const marked = middleware({...read,result});
  assert.match(marked.result.content[0].text,/untrusted tool result/);
  assert.equal(result.content[0].text,"fixture");
  assert.ok(events.every(event => event.source === "openclaw_plugin"));
  adapter.close();
});
