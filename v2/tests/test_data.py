"""Phase 1 gate: dataset integrity (critical gates 1 and 2 in implementation_mvp.md)."""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import pytest

OFFLINE = Path(__file__).resolve().parents[1] / "offline"
sys.path.insert(0, str(OFFLINE))
from templates import (  # noqa: E402
    AI_WORDS, BENIGN, BENIGN_MULTI, MULTI_SPLIT, BENIGN_HINDI, BENIGN_SPLIT, HARD_NEGATIVE_DOCS, INJECTIONS, INNOCENT_TRIGGERS, TEMPLATE_SPLIT,
    TRAINED_STYLES, TRIGGER_SPLIT, by_split, keyword_hit,
)

SPLITS = ("train", "val", "test")

ROWS = OFFLINE / "data" / "qwen0.5b" / "rows.jsonl"
SUMMARY = OFFLINE / "out" / "qwen0.5b" / "data_summary.json"
MAX_TOKENS = 400


@pytest.fixture(scope="module")
def rows():
    assert ROWS.exists(), "run offline/build_data.py first"
    return [json.loads(line) for line in ROWS.read_text(encoding="utf-8").splitlines()]


def test_ids_unique(rows):
    ids = [r["id"] for r in rows]
    assert len(ids) == len(set(ids))


def test_no_doc_in_two_splits(rows):
    splits = defaultdict(set)
    for r in rows:
        if r["split"] != "heldout":
            splits[r["doc_id"]].add(r["split"])
    leaked = {d: s for d, s in splits.items() if len(s) > 1}
    assert not leaked


def test_heldout_from_test_docs_only_with_controls(rows):
    test_docs = {r["doc_id"] for r in rows if r["split"] == "test"}
    held = [r for r in rows if r["split"] == "heldout"]
    assert held
    assert {r["doc_id"] for r in held} <= test_docs
    styles = {(r["style"], r["label"]) for r in held}
    assert ("hindi_hinglish", 1) in styles and ("benign_hindi", 0) in styles


def test_heldout_rows_are_one_to_one_pairs(rows):
    per_doc = defaultdict(list)
    for r in rows:
        if r["split"] == "heldout" and not r.get("family"):  # v1 held-out = Hindi pairs; H1 families: test_attacks
            per_doc[r["doc_id"]].append(r["style"])
    assert per_doc and all(sorted(v) == ["benign_hindi", "hindi_hinglish"] for v in per_doc.values())


def test_benign_hindi_controls_use_hindi_pool_only(rows):
    for r in rows:
        if r["style"] == "benign_hindi":
            assert r["split"] == "heldout" and r["insertion"] in BENIGN_HINDI
        elif r["insertion"]:
            assert r["insertion"] not in BENIGN_HINDI


def test_heldout_style_never_in_train_or_val(rows):
    assert not [r for r in rows if r["style"] == "hindi_hinglish" and r["split"] != "heldout"]


def test_every_clean_main_row_has_benign_insertion(rows):
    for r in rows:
        if r["style"] == "clean":
            assert r["insertion"] in BENIGN and r["insertion"] in r["output"]


def test_clean_and_injected_lengths_match_per_format(rows):
    main = [r for r in rows if r["split"] != "heldout" and r["style"] != "hard_negative" and not r.get("family")]
    for is_json in (False, True):  # v1 rows; H1 pairs are length-matched per pair (test_attacks.py)
        grp = [r for r in main if r["style"].startswith("json") == is_json]
        clean = [len(r["output"].split()) for r in grp if r["label"] == 0]
        inj = [len(r["output"].split()) for r in grp if r["label"] == 1]
        mc, mi = sum(clean) / len(clean), sum(inj) / len(inj)
        assert abs(mc - mi) / mi <= 0.10, ("json" if is_json else "prose", mc, mi)


def test_each_format_is_balanced_between_labels(rows):
    """Neither format may be mostly one label, or format itself becomes the cue."""
    main = [r for r in rows if r["split"] != "heldout" and r["style"] != "hard_negative"]
    js = [r["label"] for r in main if r["style"].startswith("json")]
    assert js and sum(js) == len(js) / 2


def test_json_rows_are_valid_json_and_carry_their_insertion(rows):
    for r in rows:
        if r["style"].startswith("json"):
            json.loads(r["output"])
            assert r["insertion"] in r["output"] and r["position"] in ("article", "product", "email", "event")


def test_json_injection_templates_disjoint_across_splits(rows):
    for split in SPLITS:
        for r in rows:
            if r["style"] == "json_tool" and r["split"] == split:
                ids = list(range(len(INJECTIONS[r["kind"]])))
                assert r["template_id"] in by_split(ids, TEMPLATE_SPLIT, split), r["id"]


def test_benign_multilingual_pool_split_and_disjoint_from_heldout_controls(rows):
    assert not set(BENIGN_MULTI) & set(BENIGN_HINDI)
    for split in SPLITS:
        used = {r["insertion"] for r in rows if r["style"] == "benign_multilingual" and r["split"] == split}
        assert used and used <= set(by_split(BENIGN_MULTI, MULTI_SPLIT, split)), split
    assert any(any("ऀ" <= c <= "ॿ" for c in r["insertion"])
               for r in rows if r["style"] == "benign_multilingual" and r["split"] == "train")


def test_templates_disjoint_across_train_val_test(rows):
    for style in TRAINED_STYLES:
        ids = list(range(len(INJECTIONS[style])))
        for split in SPLITS:
            used = {r["template_id"] for r in rows if r["style"] == style and r["split"] == split}
            assert used and used <= set(by_split(ids, TEMPLATE_SPLIT, split)), (style, split)


def test_benign_insertions_disjoint_across_splits(rows):
    for split in SPLITS:
        used = {r["insertion"] for r in rows if r["style"] == "clean" and r["split"] == split}
        assert used and used <= set(by_split(BENIGN, BENIGN_SPLIT, split)), split


def test_innocent_triggers_disjoint_across_splits(rows):
    for split in SPLITS:
        used = {r["insertion"] for r in rows if r["kind"] == "squad_trigger" and r["split"] == split}
        assert used and used <= set(by_split(INNOCENT_TRIGGERS, TRIGGER_SPLIT, split)), split


def test_no_insertion_text_shared_between_splits(rows):
    seen = defaultdict(set)
    for r in rows:
        if r["insertion"] and r["split"] in SPLITS:
            seen[r["insertion"]].add(r["split"])
    assert not {t: s for t, s in seen.items() if len(s) > 1}


def test_hard_negatives_in_every_split(rows):
    hn_splits = {r["split"] for r in rows if r["style"] == "hard_negative"}
    assert {"train", "val", "test"} <= hn_splits
    assert all(r["label"] == 0 for r in rows if r["style"] == "hard_negative")


def test_demo_hard_negative_kinds_in_test(rows):
    kinds = {r["kind"] for r in rows if r["style"] == "hard_negative" and r["split"] == "test"}
    assert {"security_blog", "recipe"} <= kinds


def test_insertion_survives_truncation(rows):
    for r in rows:
        assert r["n_tokens"] <= MAX_TOKENS, r["id"]
        pages = " ".join(r.get("prior_outputs", []) + [r["output"]])
        for part in r.get("insertion_parts") or ([r["insertion"]] if r["insertion"] else []):
            assert part in pages, r["id"]


def test_polite_style_has_no_keyword_markers(rows):
    polite = [r for r in rows if r["style"] == "polite_no_triggers"]
    assert polite
    assert not [r["id"] for r in polite if keyword_hit(r["insertion"])]


def test_user_voice_has_no_keywords_and_never_addresses_the_ai(rows):
    uv = [r for r in rows if r["style"] == "user_voice"]
    assert {r["split"] for r in uv} == set(SPLITS) and all(r["label"] == 1 for r in uv)
    for r in uv:
        words = set(re.findall(r"[a-z]+", r["insertion"].lower()))
        assert not keyword_hit(r["insertion"]) and not words & set(AI_WORDS), r["id"]


def test_every_trained_style_on_every_main_doc(rows):
    styles = defaultdict(set)
    for r in rows:
        if r["doc_id"].startswith("d") and r["split"] != "heldout" and not r.get("family"):  # v1 styles
            styles[r["doc_id"]].add(r["style"])
    expected = set(TRAINED_STYLES) | {"clean", "benign_multilingual", "json_clean", "json_tool"}
    assert all(s == expected for s in styles.values())


def test_hard_negative_docs_cover_three_kinds():
    assert {"security_blog", "recipe", "memo"} <= {k for k, _ in HARD_NEGATIVE_DOCS}


def test_summary_counts_match_rows(rows):
    s = json.loads(SUMMARY.read_text(encoding="utf-8"))
    assert s["rows"] == len(rows)
    assert sum(c["n"] for c in s["counts"]) == len(rows)
