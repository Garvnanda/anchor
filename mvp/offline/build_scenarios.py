"""Phase 3: 8 demo scenarios from test / held-out rows with their real scores → api/data/*.json."""
import json
import shutil

from common import DATA, MODEL, OUT, ROOT, SECRET, USER_EMAIL
from scenario_pick import attacker_address, pick

API_DATA = ROOT.parent / "api" / "data"
PROBE_VERSION = "v1"


def main():
    rows = [json.loads(line) for line in (DATA / "rows.jsonl").read_text(encoding="utf-8").splitlines()]
    scores = json.loads((OUT / "scores.json").read_text(encoding="utf-8"))
    actions = json.loads((OUT / "actions.json").read_text(encoding="utf-8"))
    metrics = json.loads((OUT / "metrics.json").read_text(encoding="utf-8"))
    assert "external" in metrics, "metrics.json has no external block: run external_eval.py after train_probe.py"
    by_sid = {a["scenario_id"]: a for a in actions["scenarios"]}

    scenarios = []
    for sid, title, r in pick(rows):
        a = by_sid[sid]
        assert a["row_id"] == r["id"], f"actions.json is stale for scenario {sid}"
        s = scores[r["id"]]
        scenarios.append({
            "id": sid, "title": title, "row_id": r["id"], "split": r["split"],
            "task": r["task"], "page": r["output"], "insertion": r["insertion"],
            "label": r["label"], "style": r["style"], "kind": r["kind"],
            "probe_score": s["probe_score"], "keyword_hit": s["keyword_hit"],
            "action_source": a["action_source"],
            "attacker": attacker_address(r["insertion"]) if r["label"] == 1 else None,
            "steps": [
                {"kind": "read", "tool": "fetch_page"},
                {"kind": "side_effect", "tool": "send_email",
                 "to": a["action"]["to"], "body": str(a["action"].get("body", ""))[:400]},
            ],
        })

    metrics["hijacked"] = actions["hijacked"]
    (OUT / "metrics.json").write_text(json.dumps(metrics, indent=2))
    (OUT / "scenarios.json").write_text(json.dumps(scenarios, indent=2, ensure_ascii=False), encoding="utf-8")
    meta = {"model": MODEL, "probe_version": PROBE_VERSION, "layer": metrics["layer"],
            "threshold": metrics["threshold"], "built_at": metrics["built_at"], "rows": metrics["rows"],
            "secret": SECRET, "user_email": USER_EMAIL}
    (OUT / "probe_meta.json").write_text(json.dumps(meta, indent=2))

    API_DATA.mkdir(parents=True, exist_ok=True)
    for name in ("scenarios.json", "metrics.json", "layer_sweep.json", "probe_meta.json"):
        shutil.copyfile(OUT / name, API_DATA / name)
    for s in scenarios:
        print(s["id"], s["style"], s["label"], round(s["probe_score"], 3), s["keyword_hit"], s["action_source"])


if __name__ == "__main__":
    main()
