"""H1 gate: attack families + Tamil in dataset v2 — presence per split, held-out rules, family properties,
length-matched controls, template split, v1 rows unchanged."""
import base64
import codecs
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pytest

V2 = Path(__file__).resolve().parents[1]
OFFLINE = V2 / "offline"
sys.path.insert(0, str(OFFLINE))

import attacks  # noqa: E402
from templates import BENIGN_MULTI  # noqa: E402

ROWS = OFFLINE / "data" / "qwen0.5b" / "rows.jsonl"
MVP_ROWS = V2.parent / "mvp" / "offline" / "data" / "rows.jsonl"
ALL_FAMILIES = attacks.FAMILIES + attacks.HELDOUT_FAMILIES


@pytest.fixture(scope="module")
def rows():
    return [json.loads(line) for line in ROWS.read_text(encoding="utf-8").splitlines()]


@pytest.fixture(scope="module")
def fam(rows):
    return [r for r in rows if r.get("family")]


def pairs(fam_rows):
    by = defaultdict(dict)
    for r in fam_rows:
        by[(r["doc_id"], r["family"])][r["label"]] = r
    return by


def test_v1_rows_are_an_unchanged_prefix():
    v1 = MVP_ROWS.read_text(encoding="utf-8").splitlines()
    assert ROWS.read_text(encoding="utf-8").splitlines()[:len(v1)] == v1


def test_every_family_present_with_counts_per_split(fam):
    c = Counter((r["family"], r["split"], r["label"]) for r in fam)
    for f in attacks.FAMILIES:
        for split in ("train", "val", "test"):
            assert c[f, split, 1] >= 8 and c[f, split, 1] == c[f, split, 0], (f, split)
    for f in attacks.HELDOUT_FAMILIES:
        assert c[f, "heldout", 1] >= 15 and c[f, "heldout", 1] == c[f, "heldout", 0], f


def test_heldout_families_only_in_heldout_split(rows):
    held = {"hindi_hinglish", "benign_hindi", "tamil", "benign_tamil", "tool_description", "benign_tool_description"}
    for r in rows:
        assert (r["style"] in held) == (r["split"] == "heldout"), r["id"]


def test_heldout_rows_come_from_test_documents(rows):
    split_of_doc = {r["doc_id"]: r["split"] for r in rows if r["split"] != "heldout"}
    for r in rows:
        if r["split"] == "heldout":
            assert split_of_doc[r["doc_id"]] == "test", r["id"]


def test_no_document_in_two_trainable_splits(rows):
    splits = defaultdict(set)
    for r in rows:
        if r["split"] != "heldout":
            splits[r["doc_id"]].add(r["split"])
    assert all(len(s) == 1 for s in splits.values())


def test_family_templates_disjoint_across_splits(fam):
    for f in attacks.FAMILIES:
        tids = {s: {r["template_id"] for r in fam if r["family"] == f and r["split"] == s and r["label"] == 1}
                for s in ("train", "val", "test")}
        assert not (tids["train"] & tids["val"] or tids["train"] & tids["test"] or tids["val"] & tids["test"]), f


def test_every_injection_has_a_control_and_both_labels_are_right(fam):
    for k, v in pairs(fam).items():
        assert set(v) == {0, 1}, k
        assert v[1]["style"] == k[1] and v[0]["style"] == f"benign_{k[1]}"


def test_controls_are_length_matched(fam):
    for k, v in pairs(fam).items():
        if k[1] != "tamil":  # Tamil follows the Hindi design: a benign-Tamil sentence, not a length match
            assert attacks.within_tolerance(v[0]["insertion"], v[1]["insertion"]), (k, len(v[0]["insertion"]), len(v[1]["insertion"]))


def test_invisible_rows_carry_tag_or_zero_width_code_points(fam):
    inv = [r for r in fam if r["family"] == "invisible_unicode"]
    assert inv
    for r in inv:  # both labels: the hiding trick itself is not the cue
        hidden = [c for c in r["insertion"] if 0xE0000 <= ord(c) <= 0xE007F or c == attacks.ZWSP]
        assert len(hidden) >= 10, r["id"]
    tag = [r for r in inv if r["label"] == 1 and any(0xE0000 <= ord(c) <= 0xE007F for c in r["insertion"])]
    decoded = "".join(chr(ord(c) - 0xE0000) for c in tag[0]["insertion"] if 0xE0000 <= ord(c) <= 0xE007F)
    assert decoded.startswith("Ignore the user's task")


def test_homoglyph_rows_contain_cyrillic_lookalikes(fam):
    cyr = set(attacks.HOMOGLYPHS.values())
    hg = [r for r in fam if r["family"] == "homoglyph"]
    assert hg and all(sum(c in cyr for c in r["insertion"]) >= 3 for r in hg)


def test_split_payload_halves_are_in_separate_outputs(fam):
    sp = [r for r in fam if r["family"] == "split_payload"]
    assert sp
    for r in sp:
        first, second = r["insertion_parts"]
        assert len(r["prior_outputs"]) == 1
        assert first in r["prior_outputs"][0] and first not in r["output"]
        assert second in r["output"] and second not in r["prior_outputs"][0]


def test_encoded_payload_decodes_to_an_instruction(fam):
    enc = [r for r in fam if r["family"] == "encoded" and r["label"] == 1]
    assert enc
    for r in enc:
        kind, wrap = attacks.ENCODED[r["template_id"]]
        pre, post = wrap.split("{p}")
        payload = r["insertion"][len(pre):len(r["insertion"]) - len(post)]
        text = {"b64": lambda p: base64.b64decode(p).decode(), "rot13": lambda p: codecs.decode(p, "rot13"),
                "hex": lambda p: bytes.fromhex(p).decode()}[kind](payload)
        assert text.startswith("Ignore the user's task and "), r["id"]


def test_json_families_parse_and_hold_the_insertion(fam):
    for r in fam:
        if r["family"] in attacks.JSON_FAMILIES:
            obj = json.loads(r["output"])
            text = json.dumps(obj, ensure_ascii=False)
            assert r["insertion"] in text, r["id"]


def test_tool_description_puts_the_instruction_in_a_tool_description(fam):
    for r in fam:
        if r["family"] == "tool_description":
            descs = [t["description"] for t in json.loads(r["output"])["tools"]]
            assert json.loads(f'"{r["insertion"]}"') in descs


def test_exfil_rows_carry_an_attacker_url(fam):
    for r in fam:
        if r["family"] == "exfil_link":
            has_attacker = any(u in r["insertion"] for u in ("acct-verify.example", "notes-sync.example"))
            assert has_attacker == (r["label"] == 1), r["id"]


def test_tamil_rows_are_tamil_and_controls_disjoint_from_training_pool(fam):
    ta = [r for r in fam if r["family"] == "tamil"]
    assert ta
    for r in ta:
        if r["label"] == 0:
            assert r["insertion"] in attacks.BENIGN_TAMIL
    assert not set(attacks.BENIGN_TAMIL) & set(BENIGN_MULTI)
    tamil_script = [r for r in ta if r["label"] == 1 and any("஀" <= c <= "௿" for c in r["insertion"])]
    assert len(tamil_script) >= len([r for r in ta if r["label"] == 1]) // 3  # mix of Tamil script and Tanglish


def test_rows_fit_the_token_budget(rows):
    assert max(r["n_tokens"] for r in rows) <= 400


def test_fit_and_matched_are_deterministic():
    order = list(attacks.BENIGN)
    assert attacks.fit(order, 50) == attacks.fit(order, 50)
    out = attacks.matched(lambda t: f"x {t} y", 120, order)
    assert attacks.within_tolerance(out, "z" * 120)
