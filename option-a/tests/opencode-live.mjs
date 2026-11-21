import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { copyFileSync, mkdirSync, mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { validateEvent } from "./contract.mjs";

const cache = resolve(".cache");
const executable = resolve(process.env.ANCHOR_OPENCODE ??
  join(cache, "audit/node_modules/@opencode/cli-windows-x64/bin/opencode.exe"));
const model = process.env.ANCHOR_AUDIT_MODEL ?? "qwen3:0.6b";
mkdirSync(cache, { recursive: true });
const cwd = mkdtempSync(join(cache, "a1-live-"));
console.log("A1 evidence:", cwd);
const pluginDir = join(cwd, ".opencode", "plugins");
mkdirSync(pluginDir, { recursive: true });
copyFileSync(new URL("../audit/plugin.ts", import.meta.url), join(pluginDir, "sentinel.ts"));
copyFileSync(new URL("../examples/opencode/.opencode/plugins/anchor.ts", import.meta.url), join(pluginDir, "anchor.ts"));
const output = join(cwd, "anchor.jsonl");
const config = join(cwd, "opencode.json");
const prompt = "Call the audit_sentinel tool once with no arguments ({}). After its result, reply done.";
writeFileSync(config, JSON.stringify({
  plugins: ["-opencode.fork-notice"],
  model: "ollama/" + model,
  providers: { ollama: { settings: { baseURL: "http://127.0.0.1:11434/v1" } } },
}));
const run = spawnSync(executable, ["--standalone", "run", "--title", "Anchor A1 observation",
  "--model", "ollama/" + model, prompt], {
  cwd, encoding: "utf8", timeout: 180000,
  env: { ...process.env, ANCHOR_OBSERVATION_LOG: output, ANCHOR_AUDIT_DENY: "0",
    OPENCODE_CONFIG: config, OPENCODE_DISABLE_AUTOUPDATE: "true",
    XDG_CONFIG_HOME: join(cwd, "config"), XDG_DATA_HOME: join(cwd, "data"), XDG_CACHE_HOME: join(cwd, "cache") },
});
writeFileSync(join(cwd, "cli.log"), [run.stdout, run.stderr, run.error].filter(Boolean).join("\n"));
assert.equal(run.status, 0);
assert.equal(readFileSync(join(cwd, "sentinel"), "utf8"), "marker");
const raw = readFileSync(output, "utf8");
assert.ok(!raw.includes(prompt) && !raw.includes("sentinel-created"), "Raw content appeared in event log");
const events = raw.trim().split("\n").map(line => JSON.parse(line));
const audit = readFileSync(join(cwd, "audit.jsonl"), "utf8").trim().split("\n").map(line => JSON.parse(line));
const { callId, sessionId } = audit.find(event => event.kind === "before" && event.tool === "audit_sentinel");
const started = events.find(event => event.kind === "run_started" && event.sessionId === sessionId);
assert.ok(started, "No correlated prompt event");
const matchingCall = events.filter(event => event.toolCallId === callId && event.sessionId === sessionId);
assert.deepEqual(matchingCall.map(event => event.kind), ["tool_pre_execution", "tool_output_observed", "tool_finished"]);
assert.equal(matchingCall[2].details.status, "completed");
assert.ok(matchingCall[1].details.byteCount > 0);
assert.ok(matchingCall.every(event => event.runId === started.runId));
for (const event of events) assert.ok(validateEvent(event), JSON.stringify(validateEvent.errors));
console.log(JSON.stringify({ sessionId, callId, runId: started.runId, eventCount: events.length }));
console.log("A1 live observation verified");
