"""9 demo scenarios from test / held-out rows with their real scores → out/<model>/scenarios.json; copied into
api/data/ (the replay site serves the model given here)."""
import json
import shutil

from common import ROOT, SECRET, USER_EMAIL, check_run_meta, parse
from scenario_pick import attacker_address, pick

API_DATA = ROOT.parent / "api" / "data"
PROBE_VERSION = "v2"


def main(argv=None):
    run, _ = parse(argv, __doc__)
    rows = [json.loads(line) for line in (run.data / "rows.jsonl").read_text(encoding="utf-8").splitlines()]
    scores_file = json.loads((run.out / "scores.json").read_text(encoding="utf-8"))
    actions = json.loads((run.out / "actions.json").read_text(encoding="utf-8"))
    metrics = json.loads((run.out / "metrics.json").read_text(encoding="utf-8"))
    for name, block in (("scores.json", scores_file), ("actions.json", actions), ("metrics.json", metrics)):
        check_run_meta(block.get("run_meta"), run, name)
    scores, meta_run = scores_file["scores"], metrics["run_meta"]
    assert "external" in metrics, "metrics.json has no external block: run external_eval.py after train_probe.py"
    by_sid = {a["scenario_id"]: a for a in actions["scenarios"]}

    scenarios = []
    for sid, title, r in pick(rows, scores, metrics["threshold"]):
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
    (run.out / "metrics.json").write_text(json.dumps(metrics, indent=2))
    (run.out / "scenarios.json").write_text(json.dumps({"run_meta": meta_run, "scenarios": scenarios}, indent=2,
                                                       ensure_ascii=False), encoding="utf-8")
    meta = {"run_meta": meta_run, "model": run.hf_id, "probe_version": PROBE_VERSION, "layer": metrics["layer"],
            "threshold": metrics["threshold"], "built_at": metrics["built_at"], "rows": metrics["rows"],
            "secret": SECRET, "user_email": USER_EMAIL}
    (run.out / "probe_meta.json").write_text(json.dumps(meta, indent=2))

    API_DATA.mkdir(parents=True, exist_ok=True)
    for name in ("scenarios.json", "metrics.json", "layer_sweep.json", "probe_meta.json"):
        shutil.copyfile(run.out / name, API_DATA / name)
    for s in scenarios:
        print(s["id"], s["style"], s["label"], round(s["probe_score"], 3), s["keyword_hit"], s["action_source"])


if __name__ == "__main__":
    main()
