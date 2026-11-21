import { cp, mkdir, readFile, writeFile } from "node:fs/promises";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const here = new URL("./", import.meta.url);
const at = path => new URL(path, here);
function build(script, args, cwd) {
  const result = spawnSync(process.execPath, [fileURLToPath(at(script)), ...args],
    { cwd: at(cwd), stdio: "inherit" });
  if (result.status !== 0) throw Error("Build failed: " + script);
}
build("../node_modules/typescript/bin/tsc", ["-b"], "../");
build("../apps/dashboard/build.mjs", [], "../apps/dashboard/");
for (const name of ["core", "server", "opencode"]) {
  await cp(at("../packages/" + name + "/dist"), at("dist/" + name), { recursive: true, filter: src => !src.endsWith(".tsbuildinfo") });
}
async function rewrite(file, from, to) {
  const content = await readFile(at(file), "utf8");
  await writeFile(at(file), content.replaceAll(from, to));
}
for (const file of ["opencode/index.js","opencode/index.d.ts","server/index.d.ts","server/detector-http.d.ts"]) {
  await rewrite("dist/" + file, "@anchor-ai/core", "../core/index.js");
}
await rewrite("dist/server/contracts.js", "../../../../contracts/", "../contracts/");
await cp(at("../apps/dashboard/dist"), at("dist/dashboard"), { recursive: true, filter: src => !src.endsWith("development-fixtures.json") });
await mkdir(at("dist/contracts"), { recursive: true });
for (const name of ["security-event.schema.json","detector-result.schema.json","coverage.schema.json","api.openapi.json"]) {
  await cp(at("../../contracts/" + name), at("dist/contracts/" + name));
}
await mkdir(at("dist/python"), { recursive: true });
for (const name of ["serve.py","b1_provider.py","requirements-windows.txt"]) {
  await cp(at("../python/" + name), at("dist/python/" + name));
}
await cp(at("../../v2/offline/out/qwen0.5b/probe.json"), at("dist/python/probe.json"));
const rows = (await readFile(at("../../mvp/offline/data/rows.jsonl"), "utf8")).trim().split(/\r?\n/).map(line => JSON.parse(line));
const controls = [0,1].map(label => {
  const {id, task, output} = rows.find(row => row.split === "test" && row.label === label);
  return {id, label, task, output};
});
await writeFile(at("dist/python/controls.json"), JSON.stringify(controls));
await cp(at("../../mvp/offline/common.py"), at("dist/python/common.py"));
for (const file of ["b2_parity.py","showcase_controls.py","openclaw_smoke.py","b1_smoke.mjs","b1_tools.ts"]) await cp(at("../python/" + file), at("dist/python/" + file));
import Ajv from "ajv/dist/2020.js";
import formats from "ajv-formats";
import standalone from "ajv/dist/standalone/index.js";
import { createRequire } from "node:module";
const dashboardRequire = createRequire(at("../apps/dashboard/package.json"));
const { build: bundle } = dashboardRequire("esbuild");
const validator = new Ajv({strictRequired:false,code:{source:true}});
formats(validator);
const ids = {};
for (const name of ["coverage","detector-result","security-event"]) {
  const schema = JSON.parse(await readFile(at("dist/contracts/"+name+".schema.json"),"utf8"));
  validator.addSchema(schema);
  ids[name.replaceAll("-","_")] = schema.$id;
}
const api = JSON.parse(await readFile(at("dist/contracts/api.openapi.json"),"utf8"));
for (const path of ["/health","/metadata"]) {
  const id = "https://anchor.invalid/contracts/v1/response-"+encodeURIComponent(path);
  validator.addSchema({$id:id,allOf:[api.paths[path].get.responses["200"].content["application/json"].schema]});
  ids[path.slice(1)] = id;
}
await bundle({stdin:{contents:standalone(validator,ids),resolveDir:fileURLToPath(at("../"))},
  bundle:true,platform:"node",format:"cjs",outfile:fileURLToPath(at("dist/server/validators.cjs"))});
await writeFile(at("dist/server/contracts.js"), [
  'import validators from "./validators.cjs";',
  'export const contract = name => validators[name.replaceAll("-","_")];',
  'export const responseContract = path => validators[path.slice(1)];',
].join("\n"));
