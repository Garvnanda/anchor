import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { copyFileSync, existsSync, mkdirSync, mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { join, resolve } from "node:path";

const executable = resolve(process.env.ANCHOR_OPENCODE ?? "option-a/.cache/audit/node_modules/@opencode/cli-windows-x64/bin/opencode.exe");
const model = process.env.ANCHOR_AUDIT_MODEL ?? "qwen3:0.6b";
const version = spawnSync(executable, ["--version"], { encoding: "utf8", timeout: 10000 });
assert.equal(version.status, 0, String(version.error ?? version.stderr));
assert.equal(version.stdout.trim(), "opencode v2.3.2");
const cache = resolve("option-a/.cache");
mkdirSync(cache, { recursive: true });
const root = mkdtempSync(join(cache, "sentinel-"));
console.log("Audit evidence:", root);
const runs = [];
for (const deny of [false, true]) {
  const cwd = join(root, deny ? "deny" : "allow");
  mkdirSync(join(cwd, ".opencode", "plugins"), { recursive: true });
  copyFileSync(new URL("./plugin.ts", import.meta.url), join(cwd, ".opencode", "plugins", "audit.ts"));
  const config = join(cwd, "opencode.json");
  writeFileSync(config, JSON.stringify({
    plugins: ["-opencode.fork-notice"],
    model: "ollama/" + model,
    providers: { ollama: { settings: { baseURL: "http://127.0.0.1:11434/v1" } } },
  }));
  const env = {
    ...process.env,
    XDG_CONFIG_HOME: join(cwd, "config"),
    XDG_DATA_HOME: join(cwd, "data"),
    XDG_CACHE_HOME: join(cwd, "cache"),
    OPENCODE_CONFIG: config,
    OPENCODE_DISABLE_AUTOUPDATE: "true",
    ANCHOR_AUDIT_DENY: deny ? "1" : "0",
  };
  const run = spawnSync(executable, ["--standalone", "run", "--title", "Anchor sentinel audit",
    "--model", "ollama/" + model,
    "Call the audit_sentinel tool once with no arguments ({}). After its result, reply done."],
  { cwd, env, encoding: "utf8", timeout: 180000 });
  writeFileSync(join(cwd, "cli.log"), [run.stdout, run.stderr, run.error].filter(Boolean).join("\n"));
  assert.equal(run.status, 0, "OpenCode did not finish. See " + cwd);
  const events = readFileSync(join(cwd, "audit.jsonl"), "utf8").trim().split("\n").map(line => JSON.parse(line));
  assert.equal(events.find(event => event.kind === "loaded")?.version, "2.3.2");
  const before = events.find(event => event.kind === "before" && event.tool === "audit_sentinel");
  assert.ok(before?.callId && before.sessionId, "No correlated sentinel attempt. See " + cwd);
  assert.ok(events.some(event => event.kind === "prompt" && event.sessionId === before.sessionId));
  const sentinel = join(cwd, "sentinel");
  assert.equal(existsSync(sentinel), !deny);
  const after = events.find(event => event.kind === "after" && event.callId === before.callId);
  if (deny) {
    assert.ok(events.some(event => event.kind === "denied" && event.callId === before.callId));
    assert.ok(!events.some(event => event.kind === "executed"));
    assert.notEqual(after?.status, "completed");
    assert.match(run.stderr + run.stdout, /ANCHOR_AUDIT_DENIED/);
  } else {
    assert.equal(readFileSync(sentinel, "utf8"), "marker");
    assert.equal(after?.status, "completed");
    assert.equal(after.markerResult, true);
    const order = events.map(event => event.kind);
    assert.ok(order.indexOf("before") < order.indexOf("executed"));
    assert.ok(order.indexOf("executed") < order.indexOf("after"));
  }
  runs.push({ deny, callId: before.callId, sessionId: before.sessionId, after: after?.status ?? null });
}
assert.notEqual(runs[0].sessionId, runs[1].sessionId);
console.log(JSON.stringify(runs));
console.log("A0 sentinel verified");
