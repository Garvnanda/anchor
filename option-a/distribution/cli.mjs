#!/usr/bin/env node
import { tmpdir } from "node:os";
import { join } from "node:path";
import { randomBytes } from "node:crypto";
import { fileURLToPath } from "node:url";
import { spawn } from "node:child_process";
import { createLocalServer } from "./dist/server/index.js";
import { createOpenClawAdapter } from "./openclaw.mjs";

const local = path => fileURLToPath(new URL(path, import.meta.url));
async function exercise(mode, publish) {
  const hooks = new Map();
  const adapter = createOpenClawAdapter({ mode, protectedTools: ["submit_receipt"], untrustedTools: ["read_page"] }, publish);
  adapter.register({ on: (name, handler) => hooks.set(name, handler) });
  const ctx = { sessionId: "fixture-" + mode };
  let receipts = 0;
  try {
    hooks.get("before_agent_run")({ prompt: "Read and summarize a page" }, ctx);
    const read = { toolName: "read_page", toolCallId: "page" };
    await hooks.get("before_tool_call")(read, ctx);
    hooks.get("after_tool_call")({ ...read, result: "Training fixture requests a receipt." }, ctx);
    const sink = { toolName: "submit_receipt", toolCallId: "receipt" };
    const decision = await hooks.get("before_tool_call")(sink, ctx);
    if (!decision?.block) {
      receipts++;
      hooks.get("after_tool_call")({ ...sink, result: "Receipt counted" }, ctx);
    }
    if (receipts !== (mode === "enforce" ? 0 : 1)) throw Error("Unexpected receipt count");
    console.log(JSON.stringify({ scenario: "local hook fixture", mode, receipts, reason: decision?.blockReason }));
  } finally { adapter.close(); }
}

const [command, ...args] = process.argv.slice(2);
if (command === "demo" || command === "monitor") {
  const token = randomBytes(24).toString("hex");
  const portal = await createLocalServer({ token, dashboardDirectory: local("./dist/dashboard") });
  try {
    if (command === "demo") for (const mode of ["monitor", "enforce"]) await exercise(mode, portal.publish);
    if (command === "demo" && args.includes("--qwen")) {
      const { runControls } = await import("./controls.mjs");
      await runControls(local("./dist/python/showcase_controls.py"),portal.publish);
    }
    if (!args.includes("--check")) {
      console.log("Run monitor:", portal.origin, "\nLocal bearer token:", token, "\nCtrl+C to close.");
      const controller = new AbortController();
      const stop = new Promise(resolve => process.once("SIGINT", () => { controller.abort(); resolve(); }));
      if (command === "monitor") {
        if (!args[0]) throw Error("Provide an Anchor JSONL log file");
        const { follow } = await import("./follow.mjs");
        await follow(args[0], portal.publish, controller.signal);
      } else await stop;
    }
  } finally { await portal.close(); }
} else if (command === "opencode-demo") {
  const child = spawn(process.execPath,[local("./dist/python/b1_smoke.mjs"),"--managed"],{
    stdio:"inherit",env:{...process.env, ANCHOR_PROVIDER_SCRIPT:local("./dist/python/serve.py"),
      ANCHOR_PROBE:local("./dist/python/probe.json"),ANCHOR_PACKED_OPENCODE:local("./dist/opencode/index.js"),
      ANCHOR_DEMO_DIRECTORY:process.env.ANCHOR_DEMO_DIRECTORY ?? join(tmpdir(),"anchor-opencode")}});
  child.on("exit", code => {process.exitCode = code ?? 1;});
} else if (command === "openclaw-demo") {
  const child = spawn(process.env.ANCHOR_PYTHON || "python",
    [local("./dist/python/openclaw_smoke.py"), ...(args.length ? args : ["enforce"])],
    {stdio:"inherit", env:{...process.env, ANCHOR_PACKAGE:local("./")}});
  child.on("error", error => {console.error(error.message); process.exitCode = 1;});
  child.on("exit", code => { process.exitCode = code ?? 1; });
} else if (command === "provider" || command === "controls") {
  const child = spawn(process.env.ANCHOR_PYTHON || "python", command === "controls" ? [local("./dist/python/showcase_controls.py")] : [local("./dist/python/serve.py"),
    "--probe", local("./dist/python/probe.json"), ...args], { stdio: "inherit" });
  child.on("error", e => { console.error(e.message); process.exitCode = 1; });
  child.on("exit", code => { process.exitCode = code ?? 1; });
} else {
  console.log("anchor demo [--qwen] [--check]   Run the controlled policy showcase\nanchor opencode-demo     Run the real OpenCode and Qwen round trip\nanchor openclaw-demo [enforce|monitor|read]   Run the real local agent\nanchor monitor <file>   Watch a host JSONL audit log in the portal\nanchor controls         Score two matched-profile examples using local Qwen\nanchor provider         Start local Qwen (requires Python environment and cached weights)");
  if (command && command !== "--help") process.exitCode = 2;
}
