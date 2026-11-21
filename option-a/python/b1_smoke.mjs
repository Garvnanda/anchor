import assert from "node:assert/strict";
import { spawn, spawnSync } from "node:child_process";
import { copyFileSync, mkdirSync, mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { join, resolve } from "node:path";
import { createInterface } from "node:readline";
import { once } from "node:events";
import { randomUUID } from "node:crypto";

const model = "Qwen/Qwen2.5-0.5B-Instruct";
const mode = process.argv[2];
const managed = mode === "--managed";
const profile = mode === "--profile";
assert.ok(mode === undefined || profile || managed || mode === "--parity-single" || mode === "--parity-multi");
const parity = mode !== undefined && !managed && !profile;
const single = mode === "--parity-single";
const isolate = process.argv.includes("--isolate-prompt");
const evaluate = process.argv.includes("--evaluate");
const heldout = process.argv.includes("--heldout");
assert.ok(!heldout || evaluate);
assert.ok((!isolate && !evaluate) || single, "B2 diagnostics require --parity-single");
assert.ok(!(isolate && evaluate), "Run isolation and evaluation separately");
const revision = "7ae557604adf67be50417f59c2c2f167def9a775";
const python = resolve(process.env.ANCHOR_PYTHON ?? "v2/offline/.venv/Scripts/python.exe");
const opencode = resolve(process.env.ANCHOR_OPENCODE ?? "option-a/.cache/b1/node_modules/@opencode/cli-windows-x64/bin/opencode.exe");
const version = spawnSync(opencode, ["--version"], { encoding: "utf8", timeout: 10000 });
assert.equal(version.stdout?.trim(), "opencode v2.3.2", String(version.error ?? version.stderr));
const snapshot = join(homedir(), ".cache/huggingface/hub/models--Qwen--Qwen2.5-0.5B-Instruct/snapshots", revision);
const cache = resolve(process.env.ANCHOR_DEMO_DIRECTORY ?? "option-a/.cache");
mkdirSync(cache, { recursive: true });
const cwd = profile ? join(cache,"read-page-v1") : mkdtempSync(join(cache, "b1-smoke-"));
console.log("B1 evidence", cwd);
const plugins = join(cwd, ".opencode", "plugins");
mkdirSync(plugins, { recursive: true });
copyFileSync(new URL(profile ? "./profile_tool.ts" : "./b1_tools.ts", import.meta.url), join(plugins, "tools.ts"));
if (process.env.ANCHOR_PACKED_OPENCODE) {
  const entry = resolve(process.env.ANCHOR_PACKED_OPENCODE).replaceAll("\\", "/");
  writeFileSync(join(plugins, "anchor.ts"), "export { default } from " + JSON.stringify(entry) + ";");
}
if(profile) writeFileSync(join(cwd,"tools.jsonl"),"");

const token = randomUUID();
const providerArgs = managed ? ["-B", resolve(process.env.ANCHOR_PROVIDER_SCRIPT ?? "option-a/python/serve.py"), "--snapshot", snapshot]
  : ["-B", resolve("option-a/python/b1_provider.py"), snapshot];
if (managed && process.env.ANCHOR_PROBE) providerArgs.push("--probe",process.env.ANCHOR_PROBE);
if (parity) providerArgs.push("--parity");
if (profile) providerArgs.push("--capture-profile",join(cwd,"profile.json"));
if (isolate) providerArgs.push("--isolate-prompt");
if (evaluate) providerArgs.push("--evaluate");
if (heldout) providerArgs.push("--split","heldout");
const provider = spawn(python, providerArgs, {
  env: { ...process.env, HF_HUB_OFFLINE: "1", TRANSFORMERS_OFFLINE: "1", ANCHOR_DETECTOR_TOKEN: token },
  stdio: ["ignore", "pipe", "inherit"],
});
const events = [];
const lines = createInterface({ input: provider.stdout });
try {
  const { port } = await new Promise((fulfill, reject) => {
    const timeout = setTimeout(() => reject(new Error("Provider startup timed out")), 120000);
    provider.once("error", reject);
    provider.once("exit", code => { clearTimeout(timeout); reject(new Error(`Provider exited (${code})`)); });
    lines.on("line", line => {
      const event = JSON.parse(line);
      events.push(event);
      if (event.event === "b2_evaluation_progress") console.log(`B2 evaluated ${event.completed}/${event.total}`);
      if (event.event === "ready" || (managed && event.port && event.detectorStatus === "incompatible")) { clearTimeout(timeout); fulfill(event); }
    });
  });
  const config = join(cwd, "opencode.json");
  const selected = `anchor-b1/${model}`;
  writeFileSync(config, JSON.stringify({
    plugins: ["-opencode.fork-notice"], model: selected,
    providers: { "anchor-b1": { name: "Anchor B1", env: ["ANCHOR_B1_TOKEN"],
      package: "@opencode/ai/providers/openai-compatible", settings: { baseURL: `http://127.0.0.1:${port}/v1` },
      models: { [model]: { name: model, tool: true } },
    } },
  }));
  const cli = spawn(opencode, ["--standalone", "run", "--title", "Anchor B1", "--model", selected,
    profile ? "Call read_page once with no arguments. Summarize the project bulletin in one sentence." : single ? "Call get_first_color once with no arguments. After the tool returns, reply with the color."
      : "Call get_first_color and get_second_color with no arguments. After both tools return, reply with the two colors."], {
    cwd, env: { ...process.env, ANCHOR_B1_TOKEN: token, OPENCODE_CONFIG: config,
      XDG_CONFIG_HOME: join(cwd, "config"), XDG_DATA_HOME: join(cwd, "data"), XDG_CACHE_HOME: join(cwd, "cache"),
      ANCHOR_OBSERVATION_LOG: join(cwd, "anchor.jsonl"), ANCHOR_UNTRUSTED_TOOLS: "get_first_color",
      OPENCODE_DISABLE_AUTOUPDATE: "true", ANCHOR_B2_SINGLE: single ? "1" : "0" },
    stdio: ["ignore", "pipe", "pipe"],
  });
  let output = "";
  for (const stream of [cli.stdout, cli.stderr]) stream.on("data", data => { output += data; });
  const timeout = setTimeout(() => cli.kill(), isolate ? 300000 : 180000);
  const [exitCode] = await once(cli, "close").finally(() => clearTimeout(timeout));
  writeFileSync(join(cwd, "cli.log"), output);
  assert.equal(exitCode, 0, "OpenCode failed. See cli.log");
  const tools = readFileSync(join(cwd, "tools.jsonl"), "utf8").trim().split("\n").map(JSON.parse);
  const generated = events.flatMap(event => event.tools ?? []);
  const sentBack = events.flatMap(event => event.toolResultIds ?? []);
  for (const tool of profile ? ["read_page"] : single ? ["get_first_color"] : ["get_first_color", "get_second_color"]) {
    const call = generated.find(entry => entry.name === tool);
    const observed = tools.find(entry => entry.tool === tool && entry.status === "completed");
    assert.ok(observed?.id, `Missing completed hook for ${tool}`);
    assert.deepEqual(tools.find(entry => entry.executed === tool)?.args, {});
    if (!managed) {
      assert.ok(call && sentBack.includes(call.id), `Missing model call or tool continuation for ${tool}`);
      assert.equal(observed.id, call.id, `Provider/hook ID mismatch for ${tool}`);
    }
  }
  if (process.env.ANCHOR_PACKED_OPENCODE) {
    const events = readFileSync(join(cwd, "anchor.jsonl"), "utf8").trim().split("\n").map(JSON.parse);
    assert.ok(events.some(e => e.kind === "tool_output_observed" && e.source === "opencode_plugin"));
  }
  if (managed) assert.ok(events.filter(event => event.event === "generated").length >= 2);
  assert.match(output, /blue/i);
  if (!single && !profile) assert.match(output, /green/i);
  if (parity) {
    const fixture = events.find(event => event.event === "b2_saved_fixture");
    assert.ok(fixture?.maxAbsoluteFeatureDifference <= 1e-5 && fixture?.scoreAbsoluteDifference <= 1e-6
      && fixture?.sameThresholdDecision, "Saved MVP fixture failed capture parity");
    const outcome = single ? "single_result_comparison" : "multi_result_aggregate_only";
    const measured = events.find(event => event.outcome === outcome);
    assert.ok(measured, `Missing B2 result: ${outcome}`);
    if (isolate) {
      const variants = measured.promptIsolation;
      assert.equal(variants?.length, 8);
      assert.ok(variants[0].maxAbsoluteFeatureDifference <= 1e-5, "Historical prompt reconstruction differs");
      assert.ok(variants[7].maxAbsoluteDifferenceFromLive <= 1e-5, "OpenCode prompt reconstruction differs");
    }
    console.log(JSON.stringify(measured));
  }
  if (evaluate) {
    const finished = event => event.event === "b2_evaluation_complete" || event.event === "b2_evaluation_error";
    const result = events.find(finished) ?? await new Promise((fulfill, reject) => {
      const timeout = setTimeout(() => reject(new Error("B2 evaluation timed out")), 900000);
      function cleanup() {
        clearTimeout(timeout);
        lines.off("line", onLine);
        provider.off("exit", onExit);
      }
      function onLine(line) {
        const event = JSON.parse(line);
        if (finished(event)) { cleanup(); fulfill(event); }
      }
      function onExit(code) { cleanup(); reject(new Error(`Evaluation provider exited (${code})`)); }
      lines.on("line", onLine);
      provider.once("exit", onExit);
    });
    assert.equal(result.event, "b2_evaluation_complete", result.message);
    assert.equal(result.cases.length, heldout ? 44 : 205);
    const { cases, ...summary } = result;
    console.log(JSON.stringify(summary));
  }
  console.log("B1 tool round trip verified");
} finally {
  provider.kill();
  lines.close();
  writeFileSync(join(cwd, "provider.json"), JSON.stringify(events, null, 2));
}
