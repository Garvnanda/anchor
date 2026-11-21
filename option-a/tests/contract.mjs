import Ajv2020 from "ajv/dist/2020.js";
import addFormats from "ajv-formats";
import { readFileSync } from "node:fs";

const ajv = new Ajv2020({ strictRequired: false });
addFormats(ajv);
for (const name of ["coverage", "detector-result", "security-event"]) {
  ajv.addSchema(JSON.parse(readFileSync(new URL(`../../contracts/${name}.schema.json`, import.meta.url), "utf8")));
}
export const validateEvent = ajv.getSchema("https://anchor.invalid/contracts/v1/security-event.schema.json");
