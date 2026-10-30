"""Phase 4.5: the simulation's own oracle and invalid-input list are trustworthy."""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "sim"))
import simulate  # noqa: E402

from anchor.policy import run_defence  # noqa: E402
from api.index import META, SCENARIOS, app  # noqa: E402

client = TestClient(app, raise_server_exceptions=False)


@pytest.mark.parametrize("th", [0.0, 0.25, META["threshold"] - 1e-6, META["threshold"], META["threshold"] + 1e-6, 0.99, 1.0])
def test_independent_oracle_agrees_with_api_taint_rule(th):
    for sid, s in SCENARIOS.items():
        api = {d: run_defence(s, d, th, META["secret"])["verdict"] for d in ("none", "keyword", "anchor")}
        assert simulate.expected_verdicts(s, th) == api, (sid, th)


@pytest.mark.parametrize("case", simulate.INVALID, ids=lambda c: f"{c[0]} {c[1]} {str(c[2])[:30]}")
def test_every_invalid_sim_input_gets_4xx(case):
    method, path, body = case
    res = simulate.send(client, method, path, body)
    assert 400 <= res.status_code < 500, res.status_code
