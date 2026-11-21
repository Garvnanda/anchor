"""H3: the rebuilt agent-benchmark sets — counts, hashes, comparison with the paper's labels, eval-only guard."""
import json
import sys
from pathlib import Path

import pytest

V2 = Path(__file__).resolve().parents[1]
OFFLINE = V2 / "offline"
sys.path.insert(0, str(OFFLINE))

import agentbench_sets as ab  # noqa: E402

SUMMARY = json.loads((OFFLINE / "out" / "agentbench_sets.json").read_text(encoding="utf-8"))
SETS = SUMMARY["sets"]


def test_all_four_sets_recorded_with_hashes():
    assert set(SETS) == {"agentdojo_benign", "agentdojo_pairs", "bipia_pairs", "taubench_eval"}
    for name, e in SETS.items():
        assert len(e["sha256"]) == 64 and e["rows"] == e["injected"] + e["benign"] > 0, name


def test_sizes_match_the_paper_sets():
    """Row counts of the paper's stored score files (results/*.json of benign-instruction-bench)."""
    assert SETS["agentdojo_benign"]["rows"] == 339 and SETS["agentdojo_benign"]["injected"] == 0
    assert SETS["agentdojo_pairs"]["rows"] == 1017
    assert SETS["bipia_pairs"]["rows"] == 6000 and SETS["bipia_pairs"]["injected"] == 4800
    assert SETS["taubench_eval"]["benign"] == 1533 and SETS["taubench_eval"]["injected"] == 584


def test_labels_agree_with_the_paper_except_clock_artefacts():
    assert SETS["bipia_pairs"]["vs_paper"]["labels_equal"]
    ad = SETS["agentdojo_pairs"]["vs_paper"]
    assert ad["same_rows"] and ad["positive_only_here"] == 0
    assert ad["paper_only_are_write_tools"]  # the 51 paper-only positives are timestamp-stamped write-tool outputs


def test_rebuild_is_pinned_and_frozen():
    assert SUMMARY["env"] == {"PYTHONHASHSEED": "0", "PYTHONUTF8": "1"}
    assert SUMMARY["agentdojo"] == "0.1.34"
    assert all(len(c or "") == 40 for c in SUMMARY["sources"].values()), SUMMARY["sources"]
    agentdojo_steps = [cmd for cmd in ab.steps() if str(ab.AGENTDOJO_PY) == str(cmd[0])]
    assert len(agentdojo_steps) == 4 and all(cmd[1] == ab.FROZEN_CLOCK for cmd in agentdojo_steps)


def test_frozen_clock_patches_only_the_clock_reads():
    src = (OFFLINE / "frozen_clock.py").read_text(encoding="utf-8")
    assert "cloud_drive_client.datetime = clock" in src and "email_client.datetime = clock" in src
    assert 'Email.model_fields["timestamp"].default_factory' in src
    assert "_dt.datetime =" not in src  # a global swap breaks YAML dumping (seen 2026-10-30)


def test_eval_only_guard():
    ab.assert_eval_only(["a", "b"], ["c"])
    with pytest.raises(AssertionError, match="agent-benchmark rows"):
        ab.assert_eval_only(["a", "b"], ["b", "c"])


def test_sets_are_not_committed():
    import subprocess

    assert subprocess.run(["git", "check-ignore", "-q", "v2/offline/data/agentbench/bipia_pairs.jsonl"],
                          cwd=V2.parent).returncode == 0
