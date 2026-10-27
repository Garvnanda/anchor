"use strict";
// Anchor replay UI. All data comes from /api/*; page text is always inserted as text, never as HTML.

const $ = (s) => document.querySelector(s);

function h(tag, attrs = {}, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") el.className = v;
    else if (k === "style") el.style.cssText = v;
    else el.setAttribute(k, v);
  }
  for (const k of kids.flat()) if (k != null) el.append(k instanceof Node ? k : String(k));
  return el;
}

async function api(path, body) {
  const res = await fetch(path, body ? {
    method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body),
  } : {});
  if (!res.ok) throw new Error(`${path} → ${res.status}`);
  return res.json();
}

const state = { health: null, scenarios: [], current: null, threshold: null, req: 0 };

// ---- theme -------------------------------------------------------------------------------
function currentTheme() {
  const t = document.documentElement.dataset.theme;
  if (t) return t;
  return matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}
function paintToggle() { $("#theme").textContent = currentTheme() === "dark" ? "☀ light" : "☾ dark"; }
$("#theme").addEventListener("click", () => {
  const next = currentTheme() === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  try { localStorage.setItem("anchor-theme", next); } catch (e) { /* storage blocked: theme still applies */ }
  paintToggle();
});
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", paintToggle);
paintToggle();

// ---- scenarios -----------------------------------------------------------------------------
function labelTag(s) {
  if (s.split === "heldout") return h("span", { class: "tag heldout" }, "held-out");
  return h("span", { class: `tag ${s.label ? "injected" : "clean"}` }, s.label ? "injected" : "clean");
}

function renderPicker() {
  $("#scenarios").replaceChildren(...state.scenarios.map((s) =>
    h("button", { class: "scn", type: "button", "aria-pressed": String(s.id === state.current), "data-id": s.id },
      h("span", { class: "t" }, s.title), labelTag(s),
      h("span", { class: "tag style" }, s.kind || s.style))));
}

function renderPage(scn) {
  $("#task").textContent = scn.task;
  const page = $("#page");
  const ins = scn.insertion;
  const at = ins ? scn.page.indexOf(ins) : -1;
  if (at < 0) { page.replaceChildren(scn.page); return; }
  page.replaceChildren(scn.page.slice(0, at),
    h("mark", { class: scn.label ? "" : "benign" }, ins), scn.page.slice(at + ins.length));
}

const VERDICT = { leaked: "SECRET LEAKED", safe: "SAFE", false_block: "FALSE BLOCK" };
const DEFENCE = { none: ["No defence", ""], keyword: ["Keyword filter", "baseline"], anchor: ["Anchor", "activation probe"] };

function stepCard(t, defence, th, source) {
  if (t.kind === "read") {
    let score;
    if (t.score === null) score = h("span", { class: "muted" }, "no check");
    else if (defence === "keyword") score = h("span", {}, t.score ? "keyword hit" : "no hit");
    else score = h("span", {}, `drift ${t.score.toFixed(3)}`);
    return h("div", { class: "step" },
      h("div", { class: "row" }, h("span", { class: "tool" }, t.tool), score),
      t.tainted ? h("div", { class: "row", style: "margin-top:6px" }, h("span", { class: "pill taint" }, "TAINTED")) : null,
      defence === "anchor" ? h("div", { class: "meter" },
        h("i", { style: `width:${(t.score * 100).toFixed(1)}%` }),
        h("span", { class: "th", style: `left:calc(${(th * 100).toFixed(1)}% - 1px)` })) : null);
  }
  return h("div", { class: `step${t.blocked ? " blocked" : ""}` },
    h("div", { class: "row" }, h("span", { class: "tool" }, t.tool),
      h("span", {}, t.blocked ? h("span", { class: "pill block" }, "BLOCKED") : null, " ",
        h("span", { class: "pill src", title: source === "model" ? "written by the model" : "fixed action" }, source))),
    h("div", { class: "detail" }, `to: ${t.to}`, h("br"), `body: ${t.body}`));
}

async function runScenario() {
  const id = state.current, th = state.threshold, req = ++state.req;
  try {
    const r = await api("/api/run", { scenario_id: id, threshold: th });
    if (req !== state.req) return; // a newer request superseded this one
    renderPage(r.scenario);
    $("#cols").replaceChildren(...r.results.map((res) => {
      const [name, sub] = DEFENCE[res.defence];
      return h("div", { class: "col" },
        h("h3", {}, name, h("small", {}, sub)),
        h("div", { class: "steps" }, res.turns.map((t) => stepCard(t, res.defence, r.threshold, r.scenario.action_source))),
        h("div", { class: `verdict ${res.verdict}` }, VERDICT[res.verdict]));
    }));
  } catch (e) {
    $("#cols").replaceChildren(h("p", { class: "err" }, `Could not run scenario: ${e.message}`));
  }
}

$("#scenarios").addEventListener("click", (e) => {
  const b = e.target.closest(".scn");
  if (!b) return;
  state.current = Number(b.dataset.id);
  renderPicker();
  runScenario();
});

// ---- threshold -----------------------------------------------------------------------------
function setThreshold(v) {
  state.threshold = Math.round(v * 1000) / 1000;
  $("#th").value = state.threshold;
  $("#thv").textContent = state.threshold.toFixed(3);
}
let debounce;
$("#th").addEventListener("input", (e) => {
  setThreshold(Number(e.target.value));
  clearTimeout(debounce);
  debounce = setTimeout(runScenario, 80);
});
$("#reset").addEventListener("click", () => { setThreshold(state.health.threshold); runScenario(); });

// ---- metrics -------------------------------------------------------------------------------
function pct(m) {
  if (!m || m.rate == null) return h("td", {}, "—");
  return h("td", {}, `${Math.round(m.rate * 100)}%`, h("span", { class: "n" }, `${m.hits}/${m.n}`));
}
function cell(m, other, higherIsBetter) {
  const td = pct(m);
  if (m && other && m.rate != null && other.rate != null &&
      (higherIsBetter ? m.rate > other.rate : m.rate < other.rate)) td.classList.add("win");
  return td;
}
function num(v, other) {
  const td = h("td", {}, v == null ? "—" : v.toFixed(2));
  if (v != null && other != null && v > other) td.classList.add("win");
  return td;
}

function renderMetrics({ metrics: m, layer_sweep: sweep }) {
  const a = m.anchor, k = m.keyword, ea = m.external?.anchor, ek = m.external?.keyword;
  const rows = [
    ["AUROC, test", num(k.test.auroc, null), num(a.test.auroc, k.test.auroc)],
    [`Detection rate, test (threshold at ${Math.round(m.target_fpr * 100)}% val false-positive rate)`, cell(k.test.tpr, a.test.tpr, true), cell(a.test.tpr, k.test.tpr, true)],
    ["False blocks, clean pages", cell(k.test.false_block_clean, a.test.false_block_clean, false), cell(a.test.false_block_clean, k.test.false_block_clean, false)],
    ["False blocks, hard negatives", cell(k.test.false_block_hard_negative, a.test.false_block_hard_negative, false), cell(a.test.false_block_hard_negative, k.test.false_block_hard_negative, false)],
    ["Polite injection, no trigger words", cell(k.test.per_style_tpr.polite_no_triggers, a.test.per_style_tpr.polite_no_triggers, true), cell(a.test.per_style_tpr.polite_no_triggers, k.test.per_style_tpr.polite_no_triggers, true)],
    ["JSON-shaped tool responses, detection", cell(k.test.per_style_tpr.json_tool, a.test.per_style_tpr.json_tool, true), cell(a.test.per_style_tpr.json_tool, k.test.per_style_tpr.json_tool, true)],
    ["False blocks, benign non-English pages", cell(k.test.false_block_benign_multilingual, a.test.false_block_benign_multilingual, false), cell(a.test.false_block_benign_multilingual, k.test.false_block_benign_multilingual, false)],
    ["Held-out Hindi/Hinglish detection", cell(k.heldout.per_style_tpr.hindi_hinglish, a.heldout.per_style_tpr.hindi_hinglish, true), cell(a.heldout.per_style_tpr.hindi_hinglish, k.heldout.per_style_tpr.hindi_hinglish, true)],
    ["False blocks, benign Hindi", cell(k.heldout.false_block_benign_hindi, a.heldout.false_block_benign_hindi, false), cell(a.heldout.false_block_benign_hindi, k.heldout.false_block_benign_hindi, false)],
  ];
  if (ea) {
    rows.push(["External (InjecAgent) detection", cell(ek.tpr, ea.tpr, true), cell(ea.tpr, ek.tpr, true)]);
    rows.push(["External (InjecAgent) false blocks", cell(ek.false_block, ea.false_block, false), cell(ea.false_block, ek.false_block, false)]);
  }
  rows.push(["Shuffled-label control AUROC (should be ≈ 0.5)", h("td", {}, "—"), num(m.shuffled_label_control.test_auroc, null)]);
  $("#mtable").replaceChildren(
    h("thead", {}, h("tr", {}, h("th", {}, "Metric"), h("th", {}, "Keyword"), h("th", {}, "Anchor"))),
    h("tbody", {}, rows.map(([label, kc, ac]) => h("tr", {}, h("td", {}, label), kc, ac))));
  $("#mverdict").textContent = m.verdict;
  const hj = m.hijacked;
  $("#mnote").textContent = hj
    ? `The model wrote the attacker's email itself in ${hj.hits} of ${hj.n} injected demo scenarios; the others use a scripted action (badge on the step).`
    : "";
  const best = Math.max(...sweep.map((s) => s.val_auroc));
  $("#bars").replaceChildren(...sweep.map((s) =>
    h("div", { class: `bar${s.val_auroc === best ? " best" : ""}` },
      h("span", {}, `L${s.layer}`), h("div", {}, h("i", { style: `width:${(s.val_auroc * 100).toFixed(1)}%` })),
      h("span", {}, s.val_auroc.toFixed(3)))));
}

// ---- boot ----------------------------------------------------------------------------------
(async function boot() {
  try {
    const [health, scenarios, metrics] = await Promise.all([api("/api/health"), api("/api/scenarios"), api("/api/metrics")]);
    state.health = health;
    state.scenarios = scenarios;
    $("#mode").replaceChildren(h("b", {}, health.mode.toUpperCase()),
      ` · ${health.model.split("/").pop()} · layer ${health.probe_layer} · probe ${health.probe_version}`);
    $("#f-model").textContent = `${health.model}, CPU, fp32. Probe ${health.probe_version} on layer ${health.probe_layer}, built ${health.built_at}.`;
    $("#thnote").textContent = `validation-chosen: ${health.threshold.toFixed(3)}`;
    setThreshold(health.threshold);
    renderMetrics(metrics);
    state.current = (scenarios.find((s) => s.label === 1) || scenarios[0]).id;
    renderPicker();
    await runScenario();
  } catch (e) {
    $("#mode").textContent = "API unavailable";
    $("#cols").replaceChildren(h("p", { class: "err" }, `Could not load results: ${e.message}`));
  }
})();
