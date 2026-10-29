"""check_deploy.py passes on the real app and catches a wrong metrics payload."""
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "sim"))
import check_deploy  # noqa: E402

from api.index import app  # noqa: E402


def test_app_matches_offline_run():
    assert check_deploy.check(TestClient(app)) == []


def test_detects_metrics_drift(monkeypatch):
    monkeypatch.setattr(check_deploy, "METRICS", {**check_deploy.METRICS, "threshold": 0.0})
    assert any("metrics" in p for p in check_deploy.check(TestClient(app)))
