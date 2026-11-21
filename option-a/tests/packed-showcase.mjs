import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { createRequire } from "node:module";
import { resolve } from "node:path";
const require = createRequire(new URL("../apps/dashboard/package.json", import.meta.url));
const { chromium } = require("playwright-core");
const child = spawn(process.execPath,[resolve(process.argv[2]), "demo", "--qwen"],{stdio:["ignore","pipe","inherit"]});
let browser;
try {
  const {origin, token} = await new Promise((res,rej) => {
    let output = "";
    child.on("error",rej);
    child.once("exit",code => rej(Error("CLI exited with "+code)));
    child.stdout.on("data",chunk => {
      output += chunk;
      const match = output.match(/Run monitor: (http:\/\/127\.0\.0\.1:\d+)\s+Local bearer token: ([a-f0-9]+)/);
      if (match) res({origin:match[1], token:match[2]});
    });
  });
  browser = await chromium.launch({channel:"msedge", headless:true});
  const page = await browser.newPage();
  await page.goto(origin);
  await page.locator("input").fill(token);
  await page.getByRole("button",{name:"Connect"}).click();
  await page.waitForFunction(() => document.querySelector("#status").textContent.includes("Connected"));
  assert.equal(await page.locator("#runs p").count(),4);
  const evidence = await page.locator("#timeline").textContent();
  for (const expected of ["DETECTOR_THRESHOLD","TAINTED_SIDE_EFFECT","generation_forward_pass","managed_demo"]) assert.ok(evidence.includes(expected),expected);
  console.log("Packed CLI and browser verified: four runs and correlated detector decisions.");
} finally { await browser?.close(); child.kill(); }
