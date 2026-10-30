// Phase 4 browser check. Open the site (`cd mvp && uvicorn api.index:app`, then http://127.0.0.1:8000/),
// paste this into the DevTools console (or run it via browser automation). Returns { ok, ... }.
// Checks: every scenario's on-screen verdicts / BLOCKED / TAINTED / source badge equal /api/run at the
// val threshold; the metrics table equals /api/metrics; mode badge; no horizontal scroll at this width.
(async () => {
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const post = (body) => fetch("/api/run", { method: "POST", headers: { "content-type": "application/json" },
    body: JSON.stringify(body) }).then((r) => r.json());
  const VERD = { leaked: "SECRET LEAKED", safe: "SAFE", false_block: "FALSE BLOCK" };
  const health = await fetch("/api/health").then((r) => r.json());
  const ids = (await fetch("/api/scenarios").then((r) => r.json())).map((s) => s.id);
  const out = { mismatches: [], scenarios: [] };

  for (const id of ids) {
    document.querySelector(`.scn[data-id="${id}"]`).click(); // re-query: the picker re-renders on click
    await wait(600);
    const api = await post({ scenario_id: id, threshold: health.threshold });
    const cols = [...document.querySelectorAll("#cols .col")];
    const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
    const ok = same(cols.map((c) => c.querySelector(".verdict").textContent), api.results.map((r) => VERD[r.verdict]))
      && same(cols.map((c) => !!c.querySelector(".pill.block")), api.results.map((r) => r.turns[1].blocked))
      && same(cols.map((c) => !!c.querySelector(".pill.taint")), api.results.map((r) => r.tainted))
      && cols.every((c) => c.querySelector(".pill.src").textContent === api.scenario.action_source);
    if (!ok) out.mismatches.push(id);
    out.scenarios.push(`${id}: ${api.results.map((r) => r.verdict).join(" | ")} (${api.scenario.action_source})`);
  }

  const m = (await fetch("/api/metrics").then((r) => r.json())).metrics;
  const f = (x) => (x == null ? "—" : `${Math.round(x.rate * 100)}%${x.hits}/${x.n}`);
  const n2 = (v) => (v == null ? "—" : v.toFixed(2));
  const a = m.anchor, k = m.keyword;
  const want = [
    [n2(k.test.auroc), n2(a.test.auroc)], [f(k.test.tpr), f(a.test.tpr)],
    [f(k.test.false_block_clean), f(a.test.false_block_clean)],
    [f(k.test.false_block_hard_negative), f(a.test.false_block_hard_negative)],
    [f(k.test.per_style_tpr.polite_no_triggers), f(a.test.per_style_tpr.polite_no_triggers)],
    [f(k.test.per_style_tpr.json_tool), f(a.test.per_style_tpr.json_tool)],
    [f(k.test.false_block_benign_multilingual), f(a.test.false_block_benign_multilingual)],
    [f(k.heldout.per_style_tpr.hindi_hinglish), f(a.heldout.per_style_tpr.hindi_hinglish)],
    [f(k.heldout.false_block_benign_hindi), f(a.heldout.false_block_benign_hindi)],
    [f(m.external.keyword.tpr), f(m.external.anchor.tpr)],
    [f(m.external.keyword.false_block), f(m.external.anchor.false_block)],
    ["—", n2(m.shuffled_label_control.test_auroc)],
  ];
  const got = [...document.querySelectorAll("#mtable tbody tr")].map((tr) => [tr.children[1].textContent, tr.children[2].textContent]);
  out.metricsMatch = JSON.stringify(got) === JSON.stringify(want);
  out.badge = document.querySelector("#mode").textContent;
  out.badgeOk = out.badge.startsWith("REPLAY") && out.badge.includes(`layer ${health.probe_layer}`);
  out.noHorizontalScroll = document.documentElement.scrollWidth <= document.documentElement.clientWidth;
  out.ok = !out.mismatches.length && out.metricsMatch && out.badgeOk && out.noHorizontalScroll;
  return out;
})();
