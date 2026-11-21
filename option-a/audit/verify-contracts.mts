import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";

const require = createRequire(new URL("../.cache/audit/package.json", import.meta.url));
const Ajv2020 = require("ajv/dist/2020").default;
const ajv = new Ajv2020({ strictRequired: false });
require("ajv-formats")(ajv);
const read = (name: string) =>
  JSON.parse(readFileSync(new URL("../../contracts/" + name, import.meta.url), "utf8"));
const schemas = new Map();
for (const name of ["security-event", "detector-result", "coverage"]) {
  const schema = read(name + ".schema.json");
  ajv.addSchema(schema);
  schemas.set(name, schema.$id);
}
for (const name of schemas.keys()) assert.ok(ajv.getSchema(schemas.get(name)));

type Fixture = { schema: string; valid: boolean; data: unknown };
const cases: Fixture[] = read("fixtures/cases.json");
for (const [index, fixture] of cases.entries()) {
  assert.ok(schemas.has(fixture.schema));
  const validate = ajv.getSchema(schemas.get(fixture.schema));
  assert.equal(validate(fixture.data), fixture.valid, "Fixture " + index + ": " + JSON.stringify(validate.errors));
}
const api = read("api.openapi.json");
assert.equal(api.openapi, "3.1.0");
function checkReferences(value: unknown) {
  if (!value || typeof value !== "object") return;
  for (const [key, child] of Object.entries(value)) {
    if (key === "$ref") {
      assert.equal(typeof child, "string");
      const url = new URL(child, "https://anchor.invalid/contracts/v1/api.openapi.json");
      assert.ok(ajv.getSchema(url.href), "Unresolved OpenAPI schema: " + child);
    } else checkReferences(child);
  }
}
checkReferences(api.paths);
console.log("C0 A fixtures verified", cases.length);
