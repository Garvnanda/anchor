"""Check a deployment against the offline run.  python sim/check_deploy.py <url>

Every endpoint answers 200, /api/metrics equals offline/out/<served model>/metrics.json exactly, every scenario's /api/run verdicts
equal the independent taint-rule oracle, bad input is rejected. Exits non-zero on any mismatch.
"""
import json
import sys
from pathlib import Path

V2 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(V2 / "sim"))
from simulate import META, SCN, expected_verdicts  # noqa: E402

METRICS = json.loads((V2 / "offline" / "out" / META["run_meta"]["model"] / "metrics.json").read_text(encoding="utf-8"))


def check(client):
    """Returns a list of problems (empty = deployment matches the offline run)."""
    problems = []
    for path in ("/api/health", "/api/scenarios", "/api/metrics", "/"):
        if client.get(path).status_code != 200:
            problems.append(f"{path} not 200")
    health = client.get("/api/health").json()
    if health.get("mode") != "replay" or health.get("threshold") != META["threshold"]:
        problems.append(f"health mismatch: {health}")
    if client.get("/api/metrics").json().get("metrics") != METRICS:
        problems.append("/api/metrics differs from offline/out/metrics.json")
    if len(client.get("/api/scenarios").json()) != len(SCN):
        problems.append("scenario count differs")
    for sid, scn in SCN.items():
        got = {r["defence"]: r["verdict"] for r in client.post("/api/run", json={"scenario_id": sid}).json()["results"]}
        if got != expected_verdicts(scn, META["threshold"]):
            problems.append(f"scenario {sid} verdicts {got}")
    for body, status in (({"scenario_id": 999}, 404), ({"scenario_id": 1, "threshold": 2}, 422)):
        if client.post("/api/run", json=body).status_code != status:
            problems.append(f"{body} not {status}")
    return problems


def main():
    import httpx

    with httpx.Client(base_url=sys.argv[1].rstrip("/"), timeout=20) as client:
        problems = check(client)
    print("\n".join(problems) if problems else f"OK: {sys.argv[1]} matches the offline run ({len(SCN)} scenarios)")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
