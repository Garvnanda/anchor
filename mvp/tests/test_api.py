"""Phase 3 gate: taint rule, verdicts, validation, and that every served number comes from the pipeline."""
import ast
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

MVP = Path(__file__).resolve().parents[1]
API = MVP / "api" / "index.py"
OUT = MVP / "offline" / "out"

from api.index import META, SCENARIOS, app, run_defence  # noqa: E402

client = TestClient(app)


def scn(label=1, score=0.9, kw=False, body="Here are your notes.", to="ops@evil-mail.example"):
    return {"label": label, "probe_score": score, "keyword_hit": kw, "attacker": "ops@evil-mail.example" if label else None,
            "steps": [{"kind": "read", "tool": "fetch_page"},
                      {"kind": "side_effect", "tool": "send_email", "to": to, "body": body}]}


# --- taint rule -------------------------------------------------------------------------------

def test_taint_blocks_later_email_even_with_clean_body():
    r = run_defence(scn(score=0.95, body="Here are your notes, have a nice day."), "anchor", 0.5)
    assert r["tainted"] and r["turns"][1]["blocked"] and not r["leaked"] and r["verdict"] == "safe"


def test_below_threshold_email_goes_out_and_leaks_secret():
    r = run_defence(scn(score=0.1, body=f"key {META['secret']}"), "anchor", 0.5)
    assert not r["tainted"] and not r["turns"][1]["blocked"] and r["verdict"] == "leaked"


def test_email_to_attacker_counts_as_leak_without_secret():
    r = run_defence(scn(score=0.1, body="notes"), "none", 0.5)
    assert r["verdict"] == "leaked"


def test_clean_page_blocked_is_false_block():
    r = run_defence(scn(label=0, score=0.9, to=META["user_email"]), "anchor", 0.5)
    assert r["verdict"] == "false_block" and not r["leaked"]


def test_read_step_is_never_blocked():
    r = run_defence(scn(score=0.99), "anchor", 0.0)
    assert r["turns"][0]["blocked"] is False


# --- served scenarios ---------------------------------------------------------------------------

def run(sid, threshold=None):
    body = {"scenario_id": sid} if threshold is None else {"scenario_id": sid, "threshold": threshold}
    res = client.post("/api/run", json=body)
    assert res.status_code == 200, res.text
    return {r["defence"]: r for r in res.json()["results"]}


def test_none_leaks_on_every_injected_scenario():
    for sid, s in SCENARIOS.items():
        if s["label"] == 1:
            assert run(sid)["none"]["verdict"] == "leaked", sid


def test_clean_scenarios_never_leak():
    for sid, s in SCENARIOS.items():
        if s["label"] == 0:
            for d, r in run(sid).items():
                assert r["verdict"] in ("safe", "false_block"), (sid, d)


def test_clean_report_scenario_passes_none_and_keyword():
    r = run(1)
    assert r["none"]["verdict"] == "safe" and r["keyword"]["verdict"] == "safe"
    expected = "false_block" if SCENARIOS[1]["probe_score"] >= META["threshold"] else "safe"
    assert r["anchor"]["verdict"] == expected


def test_anchor_verdict_follows_stored_score():
    for sid, s in SCENARIOS.items():
        blocked = s["probe_score"] >= META["threshold"]
        assert run(sid)["anchor"]["turns"][1]["blocked"] == blocked, sid


def test_demo_includes_a_real_anchor_miss():
    """Scenario 9 is a held-out Hindi injection the probe scores below the threshold: Anchor lets it leak."""
    s = SCENARIOS[9]
    assert s["split"] == "heldout" and s["style"] == "hindi_hinglish" and s["probe_score"] < META["threshold"]
    assert run(9)["anchor"]["verdict"] == "leaked"


def test_keyword_threshold_fixed():
    for sid in SCENARIOS:
        assert run(sid, 0.0)["keyword"] == run(sid, 1.0)["keyword"], sid


# --- endpoints and validation ---------------------------------------------------------------

def test_health_reports_replay_mode():
    h = client.get("/api/health").json()
    assert h["mode"] == "replay" and h["model"] == META["model"] and h["probe_layer"] == META["layer"]


def test_scenarios_and_metrics_endpoints():
    assert len(client.get("/api/scenarios").json()) == 9
    m = client.get("/api/metrics").json()
    assert m["metrics"] == json.loads((OUT / "metrics.json").read_text()) and m["layer_sweep"]


@pytest.mark.parametrize("body,status", [
    ({"scenario_id": 999}, 404),
    ({"scenario_id": 1, "threshold": 1.5}, 422),
    ({"scenario_id": 1, "threshold": -0.1}, 422),
    ({"scenario_id": 1, "threshold": "high"}, 422),
    ({"scenario_id": "x"}, 422),
    ({"scenario_id": 1, "extra": 1}, 422),
    ({}, 422),
    ({"scenario_id": True}, 422),
    ({"scenario_id": "1"}, 422),
    ({"scenario_id": 1, "threshold": "0.5"}, 422),
    ({"scenario_id": 1, "threshold": True}, 422),
    ({"scenario_id": 1, "threshold": 0}, 200),
    ({"scenario_id": 1, "threshold": 1}, 200),
])
def test_validation(body, status):
    assert client.post("/api/run", json=body).status_code == status


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-Infinity"])
def test_non_finite_threshold_is_422_not_500(value):
    res = client.post("/api/run", content=f'{{"scenario_id": 1, "threshold": {value}}}'.encode(),
                      headers={"content-type": "application/json"})
    assert res.status_code == 422


def test_chunked_oversized_body_rejected():
    """No Content-Length header: the cap must count the bytes that actually arrive."""
    def chunks():
        yield b'{"scenario_id": 1, "threshold": 0.5'
        for _ in range(10):
            yield b" " * 1024
        yield b"}"
    res = client.post("/api/run", content=chunks(), headers={"content-type": "application/json"})
    assert res.status_code == 413


def test_chunked_small_body_accepted():
    def chunks():
        yield b'{"scenario_id": 1,'
        yield b' "threshold": 0.5}'
    res = client.post("/api/run", content=chunks(), headers={"content-type": "application/json"})
    assert res.status_code == 200


def test_requirements_pinned():
    lines = [l.strip() for l in (MVP / "requirements.txt").read_text().splitlines() if l.strip()]
    assert lines and all("==" in l for l in lines), lines


def test_oversized_body_rejected():
    res = client.post("/api/run", content=b'{"scenario_id": 1, "pad": "' + b"x" * 5000 + b'"}',
                      headers={"content-type": "application/json"})
    assert res.status_code == 413


def test_malformed_json_rejected():
    res = client.post("/api/run", content=b"{not json", headers={"content-type": "application/json"})
    assert res.status_code == 422


# --- provenance -----------------------------------------------------------------------------

def test_no_ml_imports():
    tree = ast.parse(API.read_text(encoding="utf-8"))
    mods = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    mods |= {n.module.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
    assert not mods & {"torch", "numpy", "sklearn", "transformers"}


def test_data_from_pipeline():
    scores = json.loads((OUT / "scores.json").read_text())
    for s in SCENARIOS.values():
        assert scores[s["row_id"]]["probe_score"] == s["probe_score"]
        assert scores[s["row_id"]]["keyword_hit"] == s["keyword_hit"]
        assert s["split"] in ("test", "heldout")


def test_action_source_matches_actions_file():
    actions = {a["scenario_id"]: a for a in json.loads((OUT / "actions.json").read_text(encoding="utf-8"))["scenarios"]}
    for sid, s in SCENARIOS.items():
        assert s["action_source"] in ("model", "scripted")
        assert s["action_source"] == actions[sid]["action_source"]
        assert s["steps"][1]["to"] == actions[sid]["action"]["to"]


def test_api_data_matches_offline_out():
    for name in ("scenarios.json", "metrics.json", "layer_sweep.json", "probe_meta.json"):
        assert (MVP / "api" / "data" / name).read_text(encoding="utf-8") == (OUT / name).read_text(encoding="utf-8")
