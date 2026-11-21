import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { Ajv2020 } from "ajv/dist/2020.js";
import type { AnySchema } from "ajv/dist/2020.js";

const require = createRequire(import.meta.url);
const ajv = new Ajv2020({ strictRequired: false });
require("ajv-formats")(ajv);
const read = (name: string) => JSON.parse(readFileSync(new URL("../../../../contracts/" + name, import.meta.url), "utf8"));
const base = "https://anchor.invalid/contracts/v1/";
for (const name of ["coverage", "detector-result", "security-event"]) ajv.addSchema(read(name + ".schema.json"));
const api = read("api.openapi.json");

export function contract(name: "coverage" | "detector-result" | "security-event") {
  const check = ajv.getSchema(base + name + ".schema.json");
  if (!check) throw new Error("Missing Anchor schema " + name);
  return check;
}

export function responseContract(path: string) {
  const schema: AnySchema = api.paths[path].get.responses["200"].content["application/json"].schema;
  return ajv.compile({ $id: base + "response-" + encodeURIComponent(path), allOf: [schema] });
}
