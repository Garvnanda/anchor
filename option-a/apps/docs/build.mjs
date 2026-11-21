import { copyFile, mkdir, readFile } from "node:fs/promises";
const source = new URL("./index.html", import.meta.url);
const destination = new URL("./dist/", import.meta.url);
const contracts = new URL("../../../contracts/", import.meta.url);
const html = await readFile(source, "utf8");
for (const [, target] of html.matchAll(/href="#([^"]+)"/g)) {
  if (!html.includes('id="' + target + '"')) throw Error("Missing navigation target " + target);
}
await mkdir(new URL("contracts/",destination),{recursive:true});
await copyFile(source,new URL("index.html",destination));
for(const file of ["api.openapi.json","security-event.schema.json","detector-result.schema.json","coverage.schema.json"]){
  await copyFile(new URL(file,contracts),new URL("contracts/"+file,destination));
}
console.log("Built guide and four versioned reference files.");
