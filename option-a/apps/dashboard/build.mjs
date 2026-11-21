import { mkdir, readFile, copyFile, writeFile } from "node:fs/promises";
import { build } from "esbuild";
import Ajv from "ajv/dist/2020.js";
import formats from "ajv-formats";
import standalone from "ajv/dist/standalone/index.js";
const root = new URL("../../../contracts/", import.meta.url);
const output = new URL("./dist/", import.meta.url);
await mkdir(output, { recursive: true });
const validator = new Ajv({ strict: false, code: { source: true } });
formats(validator);
const ids = {};
for (const [key, file] of Object.entries({
  validateEvent: "security-event",
  validateCoverage: "coverage",
  validateDetector: "detector-result",
})) {
  const schema = JSON.parse(
    await readFile(new URL(file + ".schema.json", root)),
  );
  validator.addSchema(schema);
  ids[key] = schema.$id;
}
await writeFile(new URL("validate.cjs", output), standalone(validator, ids));
await build({
  entryPoints: ["app.mjs"],
  bundle: true,
  outfile: "dist/app.js",
  platform: "browser",
});
await Promise.all(
  ["index.html", "style.css"].map((name) =>
    copyFile(name, new URL(name, output)),
  ),
);
if (process.argv.includes("--fixtures")) {
  const samples = JSON.parse(
    await readFile(new URL("fixtures/cases.json", root)),
  );
  const events = samples
    .filter((c) => c.valid && c.schema === "security-event")
    .map((c, i) => ({ ...c.data, eventId: "fixture-" + i, sequence: i + 1 }));
  await writeFile(
    new URL("development-fixtures.json", output),
    JSON.stringify(events),
  );
} else {
  const { rm } = await import("node:fs/promises");
  await rm(new URL("development-fixtures.json", output), { force: true });
}
