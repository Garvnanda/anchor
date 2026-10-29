"""Phase 4.5: 1,000 seeded simulated users against the replay API. See sim/users.md for the input mix."""
import json
import math
import random
import statistics
import sys
import time
from collections import Counter
from pathlib import Path

MVP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MVP))

from fastapi.testclient import TestClient  # noqa: E402

from api.index import app  # noqa: E402

N_USERS = 1000
SEED = 0
DATA = MVP / "api" / "data"
SCN = {s["id"]: s for s in json.loads((DATA / "scenarios.json").read_text(encoding="utf-8"))}
META = json.loads((DATA / "probe_meta.json").read_text())
METRICS = json.loads((MVP / "offline" / "out" / "metrics.json").read_text())


def expected_verdicts(s, th):
    """Independent re-implementation of the taint rule (deliberately not imported from the API)."""
    out = {}
    for d in ("none", "keyword", "anchor"):
        tainted = (d == "keyword" and s["keyword_hit"]) or (d == "anchor" and s["probe_score"] >= th)
        email = s["steps"][1]
        sent = not tainted
        leaked = sent and (META["secret"] in email["body"] or (s["attacker"] is not None and email["to"] == s["attacker"]))
        out[d] = "leaked" if leaked else ("false_block" if s["label"] == 0 and tainted else "safe")
    return out


def valid_action(rng):
    r = rng.random()
    if r < 0.15:
        return ("GET", "/api/health", None, "health")
    if r < 0.25:
        return ("GET", "/api/scenarios", None, "scenarios")
    if r < 0.35:
        return ("GET", "/api/metrics", None, "metrics")
    sid = rng.choice(list(SCN))
    t = META["threshold"]
    th = rng.choice([None, rng.random(), 0.0, 1.0, t, min(1.0, t + 1e-6), max(0.0, t - 1e-6)])
    body = {"scenario_id": sid} if th is None else {"scenario_id": sid, "threshold": th}
    return ("POST", "/api/run", body, "run")


INVALID = [
    ("POST", "/api/run", {"scenario_id": 999}),
    ("POST", "/api/run", {"scenario_id": 1, "threshold": 1.5}),
    ("POST", "/api/run", {"scenario_id": 1, "threshold": -0.2}),
    ("POST", "/api/run", b'{"scenario_id": 1, "threshold": NaN}'),
    ("POST", "/api/run", {"scenario_id": 1, "threshold": "high"}),
    ("POST", "/api/run", {"scenario_id": "one"}),
    ("POST", "/api/run", {}),
    ("POST", "/api/run", {"scenario_id": 1, "admin": True}),
    ("POST", "/api/run", b"{not json"),
    ("POST", "/api/run", b'{"scenario_id": 1, "pad": "' + b"x" * 10000 + b'"}'),
    ("GET", "/api/run", None),
    ("POST", "/api/health", {}),
    ("GET", "/api/does-not-exist", None),
    ("POST", "/api/run", [1, 2, 3]),
    # from the Phase 3 security run
    ("POST", "/api/run", b'{"scenario_id": 1, "threshold": Infinity}'),
    ("POST", "/api/run", {"scenario_id": True}),
    ("POST", "/api/run", {"scenario_id": 1, "threshold": "0.5"}),
    ("POST", "/api/run", b'{"scenario_id": 1, "scenario_id": 2}'),
    ("POST", "/api/run", ("chunked", [b'{"scenario_id": 1, "threshold": 0.5'] + [b" " * 1024] * 8 + [b"}"])),
]


def send(client, method, path, body):
    if isinstance(body, tuple):  # ("chunked", parts): no Content-Length, body streamed in parts
        return client.request(method, path, content=iter(body[1]), headers={"content-type": "application/json"})
    if isinstance(body, bytes):
        return client.request(method, path, content=body, headers={"content-type": "application/json"})
    if body is None:
        return client.request(method, path)
    return client.request(method, path, json=body)


def main():
    """`--url http://127.0.0.1:8000` runs the same sessions over real HTTP (uvicorn / vercel dev); default in-process."""
    rng = random.Random(SEED)
    url = sys.argv[sys.argv.index("--url") + 1] if "--url" in sys.argv else None
    if url:
        import httpx

        client = httpx.Client(base_url=url, timeout=10)
    else:
        client = TestClient(app, raise_server_exceptions=False)
    lat, fails, stats = [], [], Counter()
    for user in range(N_USERS):
        for _ in range(rng.randint(3, 8)):
            invalid = rng.random() < 0.10
            if invalid:
                method, path, body = rng.choice(INVALID)
                kind = "invalid"
            else:
                method, path, body, kind = valid_action(rng)
            t0 = time.perf_counter()
            try:
                res = send(client, method, path, body)
            except Exception as e:  # noqa: BLE001 — a crash is exactly what we are counting
                fails.append({"user": user, "kind": "crash", "path": path, "error": repr(e)})
                stats["crash"] += 1
                continue
            lat.append((time.perf_counter() - t0) * 1000)
            stats[kind] += 1
            if res.status_code >= 500:
                fails.append({"user": user, "kind": "5xx", "path": path, "status": res.status_code})
            elif invalid:
                if not 400 <= res.status_code < 500:
                    fails.append({"user": user, "kind": "invalid_accepted", "path": path, "body": str(body)[:80],
                                  "status": res.status_code})
            elif res.status_code != 200:
                fails.append({"user": user, "kind": "valid_rejected", "path": path, "status": res.status_code})
            elif kind == "health" and res.json()["mode"] != "replay":
                fails.append({"user": user, "kind": "health_mode"})
            elif kind == "scenarios" and len(res.json()) != len(SCN):
                fails.append({"user": user, "kind": "scenario_count"})
            elif kind == "metrics" and res.json()["metrics"] != METRICS:
                fails.append({"user": user, "kind": "metrics_mismatch"})
            elif kind == "run":
                j = res.json()
                th = body.get("threshold", META["threshold"])
                exp = expected_verdicts(SCN[body["scenario_id"]], th)
                got = {r["defence"]: r["verdict"] for r in j["results"]}
                if got != exp or not math.isclose(j["threshold"], th):
                    fails.append({"user": user, "kind": "verdict_mismatch", "body": body, "got": got, "expected": exp})

    valid_n = sum(v for k, v in stats.items() if k not in ("invalid", "crash"))
    by_kind = Counter(f["kind"] for f in fails)
    p95 = statistics.quantiles(lat, n=20)[18] if len(lat) >= 20 else max(lat)
    valid_err = sum(by_kind[k] for k in ("valid_rejected", "health_mode", "scenario_count", "metrics_mismatch",
                                         "verdict_mismatch")) / max(valid_n, 1)
    report = {
        "users": N_USERS, "target": url or "in-process", "requests": sum(stats.values()), "by_kind": dict(stats),
        "failures": dict(by_kind), "valid_error_rate": round(valid_err, 5),
        "invalid_rejected_rate": round(1 - by_kind["invalid_accepted"] / max(stats["invalid"], 1), 5),
        "p50_ms": round(statistics.median(lat), 2), "p95_ms": round(p95, 2),
        "examples": fails[:10],
    }
    report["pass"] = (by_kind["crash"] == 0 and by_kind["5xx"] == 0 and valid_err < 0.01
                      and by_kind["invalid_accepted"] == 0 and by_kind["verdict_mismatch"] == 0 and p95 < 200)
    (Path(__file__).parent / ("report_http.json" if url else "report.json")).write_text(json.dumps(report, indent=2, default=str))
    print(json.dumps({k: v for k, v in report.items() if k != "examples"}, indent=2))
    sys.exit(0 if report["pass"] else 1)


if __name__ == "__main__":
    main()
