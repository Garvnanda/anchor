"""H4: live scorer (real Qwen 0.5B) and the live API (fake scorer for the HTTP behaviour)."""
import json
import sys
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

V2 = Path(__file__).resolve().parents[1]
OFFLINE = V2 / "offline"
sys.path.insert(0, str(V2))
sys.path.insert(0, str(OFFLINE))

from api import index, live  # noqa: E402
from common import Run  # noqa: E402

QWEN = Run("qwen0.5b", "fp32")
ROWS = {json.loads(line)["id"]: json.loads(line)
        for line in (OFFLINE / "data" / "qwen0.5b" / "rows.jsonl").read_text(encoding="utf-8").splitlines()}
SCORES = json.loads((OFFLINE / "out" / "qwen0.5b" / "scores.json").read_text())["scores"]


# --- real scorer ----------------------------------------------------------------------------------------------------

@pytest.fixture(scope="module")
def scorer():
    from anchor.scorer import Scorer

    s = Scorer(QWEN)
    yield s
    del s.model


def row(pred):
    return next(ROWS[i] for i in SCORES if pred(ROWS[i]))


def test_live_score_equals_the_offline_pipeline(scorer):
    for r in (row(lambda r: r["style"] == "clean"), row(lambda r: r["style"] == "html_comment"),
              row(lambda r: r["style"] == "json_tool")):
        got = scorer.score(r["task"], r["output"])
        assert got["drift_score"] == pytest.approx(SCORES[r["id"]]["probe_score"], abs=2e-4), r["id"]
        assert got["tainted"] == (got["drift_score"] >= scorer.threshold) and not got["fail_closed"]


def test_split_payload_is_scored_with_its_earlier_page(scorer):
    r = row(lambda r: r.get("family") == "split_payload" and r["label"] == 1)
    with_prior = scorer.score(r["task"], r["output"], r["prior_outputs"])["drift_score"]
    alone = scorer.score(r["task"], r["output"])["drift_score"]
    assert with_prior == pytest.approx(SCORES[r["id"]]["probe_score"], abs=2e-4)
    assert with_prior != alone


def test_long_output_scored_as_head_and_tail(scorer):
    r = row(lambda r: r["style"] == "clean")
    long = " ".join([r["output"]] * 6)
    got = scorer.score(r["task"], long)
    assert got["truncated"] and 0.0 <= got["drift_score"] <= 1.0


def test_empty_output_is_skipped_as_clean(scorer):
    got = scorer.score("Summarize this page.", "   ")
    assert got["skipped"] and got["drift_score"] == 0.0 and not got["tainted"]


def test_attribution_spans_come_from_the_input(scorer):
    r = row(lambda r: r["style"] == "visible_imperative")
    live_spans = scorer.score(r["task"], r["output"], attribution="projection")["attribution"]
    loo = scorer.leave_one_out(r["task"], r["output"])  # offline reference: one pass per sentence, too slow live
    for spans in (live_spans, loo):
        assert spans and all(r["output"][a["start"]:a["end"]] == a["text"] for a in spans)
    assert [(a["start"], a["end"]) for a in live_spans] == [(a["start"], a["end"]) for a in loo]


def test_error_fails_closed(scorer, monkeypatch):
    monkeypatch.setattr(scorer, "raw_score", lambda *a, **k: 1 / 0)
    got = scorer.score("t", "o")
    assert got["fail_closed"] and got["tainted"] and "ZeroDivisionError" in got["reason"]


def test_timeout_fails_closed(scorer, monkeypatch):
    monkeypatch.setattr(scorer, "timeout_s", 0.05)
    monkeypatch.setattr(scorer, "raw_score", lambda *a, **k: time.sleep(0.5) or {"drift_score": 0.0, "skipped": False})
    got = scorer.score("t", "o")
    assert got["fail_closed"] and got["tainted"] and "timeout" in got["reason"]
    time.sleep(0.6)  # let the slow call finish before the next test uses the worker


def test_scorer_refuses_a_probe_of_another_precision(tmp_path, monkeypatch):
    import common
    from anchor.scorer import Scorer

    monkeypatch.setattr(common, "OUT_ROOT", tmp_path)
    (tmp_path / "llama3b").mkdir()
    (tmp_path / "llama3b" / "probe.json").write_text(json.dumps({"run_meta": {"model": "llama3b", "precision": "bf16"}}))
    with pytest.raises(common.RunMismatch):
        Scorer(Run("llama3b", "nf4"), tok=object(), model=object())


# --- live API with a fake scorer --------------------------------------------------------------------------------------

class FakeScorer:
    probe = {"run_meta": {"model": "qwen0.5b", "precision": "fp32"}}

    def __init__(self, result=None):
        self.result = result or {"drift_score": 0.9, "tainted": True, "fail_closed": False, "threshold": 0.43}
        self.calls = []

    def score(self, task, output, prior=(), attribution=None):
        self.calls.append((task, output, tuple(prior), attribution))
        return dict(self.result)


@pytest.fixture()
def client(monkeypatch):
    fake = FakeScorer()
    live.set_scorer(fake)
    monkeypatch.setattr(live, "limiter", live.RateLimit(n=1000))
    yield TestClient(live.app), fake


def test_score_endpoint_returns_the_scorer_result(client):
    c, fake = client
    res = c.post("/api/score", json={"task": "Summarize.", "output": "Page text.", "prior_outputs": ["p1"]})
    assert res.status_code == 200 and res.json()["drift_score"] == 0.9
    assert fake.calls == [("Summarize.", "Page text.", ("p1",), None)]


@pytest.mark.parametrize("body", [
    {"task": "", "output": "x"}, {"task": "t" * 501, "output": "x"}, {"task": "t", "output": "x" * 8001},
    {"task": "t", "output": "x", "extra": 1}, {"task": 1, "output": "x"}, {"task": "t"},
    {"task": "t", "output": "x", "prior_outputs": ["a"] * 4}, {"task": "t", "output": "x", "prior_outputs": ["y" * 8001]},
    {"task": "t", "output": "x", "attribution": "shap"},
])
def test_score_validation(client, body):
    assert client[0].post("/api/score", json=body).status_code == 422


def test_score_body_cap_and_replay_cap_unchanged(client):
    c, _ = client
    assert c.post("/api/score", content=b'{"task":"t","output":"' + b"x" * 40000 + b'"}',
                  headers={"content-type": "application/json"}).status_code == 413
    assert c.post("/api/run", content=b'{"scenario_id": 1, "pad": "' + b"x" * 5000 + b'"}',
                  headers={"content-type": "application/json"}).status_code == 413


def test_duplicate_keys_rejected_on_score(client):
    res = client[0].post("/api/score", content=b'{"task":"a","task":"b","output":"x"}',
                         headers={"content-type": "application/json"})
    assert res.status_code == 422


def test_rate_limit(monkeypatch):
    live.set_scorer(FakeScorer())
    monkeypatch.setattr(live, "limiter", live.RateLimit(n=2, window_s=60))
    c = TestClient(live.app)
    codes = [c.post("/api/score", json={"task": "t", "output": "x"}).status_code for _ in range(3)]
    assert codes == [200, 200, 429]


def test_rate_limit_window_slides():
    t = [0.0]
    rl = live.RateLimit(n=1, window_s=10, clock=lambda: t[0])
    assert rl.allow("a") and not rl.allow("a") and rl.allow("b")
    t[0] = 10.0
    assert rl.allow("a")


def test_fail_closed_is_503(monkeypatch):
    live.set_scorer(FakeScorer({"drift_score": None, "tainted": True, "fail_closed": True, "reason": "scorer timeout"}))
    monkeypatch.setattr(live, "limiter", live.RateLimit(n=1000))
    res = TestClient(live.app).post("/api/score", json={"task": "t", "output": "x"})
    assert res.status_code == 503 and res.json()["tainted"] is True


def test_no_scorer_fails_closed(monkeypatch):
    monkeypatch.setattr(live, "_scorer", None)
    monkeypatch.setattr(live, "set_scorer", lambda s: (_ for _ in ()).throw(RuntimeError("no model")))
    monkeypatch.setattr(live, "limiter", live.RateLimit(n=1000))
    import anchor.scorer

    monkeypatch.setattr(anchor.scorer, "Scorer", lambda run: object())
    res = TestClient(live.app).post("/api/score", json={"task": "t", "output": "x"})
    assert res.status_code == 503 and res.json()["fail_closed"] is True


def test_health_reports_live_mode(client):
    h = client[0].get("/api/health").json()
    assert h["mode"] == "live" and h["live_run_meta"]["model"] == "qwen0.5b"


def test_static_site_mount_stays_last():
    from starlette.routing import Mount

    routes = live.app.router.routes
    assert not any(isinstance(r, Mount) for r in routes[:-1])
    assert any(getattr(r, "path", None) == "/api/score" for r in routes)


def test_replay_module_has_no_ml_imports():
    import ast

    tree = ast.parse((V2 / "api" / "index.py").read_text(encoding="utf-8"))
    mods = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    mods |= {n.module.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
    assert not mods & {"torch", "numpy", "sklearn", "transformers"}
    assert index.MAX_BODY == 2048


@pytest.fixture(autouse=True, scope="module")
def _back_to_replay_mode():
    """Other test modules import the same app: leave it in replay mode."""
    yield
    index.LIVE.clear()
    live._scorer = None
