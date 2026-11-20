"""H2: baselines on the probe's rows — same rows, val-only thresholds at 5 % and 1 % FPR, per-family metrics,
licence/revision per detector, the length+position control."""
import json
import sys
from pathlib import Path

import numpy as np
import pytest

V2 = Path(__file__).resolve().parents[1]
OFFLINE = V2 / "offline"
sys.path.insert(0, str(OFFLINE))

import baselines  # noqa: E402
from train_probe import threshold_at_fpr  # noqa: E402

OUT = OFFLINE / "out" / "qwen0.5b"
B = json.loads((OUT / "baselines.json").read_text(encoding="utf-8"))
S = json.loads((OUT / "baseline_scores.json").read_text(encoding="utf-8"))
ROWS = [json.loads(line) for line in (OFFLINE / "data" / "qwen0.5b" / "rows.jsonl").read_text(encoding="utf-8").splitlines()]
RUN = ["keyword", "length_position", "pipelock"]  # Prompt Guard 2 joins when gated access is granted


def test_cpu_detectors_present_with_licence_and_revision():
    assert set(RUN) <= set(B["detectors"])
    for name, d in B["detectors"].items():
        assert d["licence"] and d["revision"] and d["training_overlap"], name


@pytest.mark.parametrize("name", RUN)
def test_every_row_scored(name):
    assert list(S["scores"][name]) == [r["id"] for r in ROWS]


@pytest.mark.parametrize("name", RUN)
@pytest.mark.parametrize("tag,fpr", [("fpr_0.05", 0.05), ("fpr_0.01", 0.01)])
def test_thresholds_come_from_val_only(name, tag, fpr):
    scores = np.array([S["scores"][name][r["id"]] for r in ROWS])
    y = np.array([r["label"] for r in ROWS])
    va = np.array([r["split"] == "val" for r in ROWS])
    d = B["detectors"][name]
    assert d["thresholds"][tag] == round(threshold_at_fpr(scores[va], y[va], fpr), 6)
    assert d[tag]["val_fpr"]["rate"] <= fpr


@pytest.mark.parametrize("name", RUN)
def test_per_family_metrics_with_counts(name):
    test, held = B["detectors"][name]["fpr_0.05"]["test"], B["detectors"][name]["fpr_0.05"]["heldout"]
    for fam in ("encoded", "invisible_unicode", "homoglyph", "split_payload", "rag_document", "exfil_link"):
        assert test["per_style_tpr"][fam]["n"] > 0 and f"false_block_benign_{fam}" in test
    for fam in ("hindi_hinglish", "tamil", "tool_description"):
        assert held["per_style_tpr"][fam]["n"] > 0
    assert test["false_block_hard_negative"]["n"] > 0 and test["auroc"] is not None


def test_length_position_control_reported():
    lp = B["detectors"]["length_position"]
    assert lp["fpr_0.05"]["test"]["auroc"] is not None and "control" in lp["training_overlap"]


def test_binary_detectors_also_at_their_native_rule():
    for name, thr in baselines.NATIVE.items():
        assert B["detectors"][name]["native"]["threshold"] == thr


def test_detectors_read_every_page():
    r = {"output": "second", "prior_outputs": ["first"]}
    assert baselines.text_of(r) == "first\n\nsecond"


def test_pipelock_unmodified_binary_and_config_hash():
    d = B["detectors"]["pipelock"]
    assert d["revision"] == "v3.7.1" and len(d["config_sha256"]) == 64


def test_prompt_guard_revisions_pinned():
    for name, (repo, rev) in baselines.PROMPT_GUARD.items():
        assert repo.startswith("meta-llama/Llama-Prompt-Guard-2-") and len(rev) == 40
