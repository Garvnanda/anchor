"""Phase 5: every number in the README's MVP results block comes from offline/out/metrics.json."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
METRICS = json.loads((ROOT / "mvp" / "offline" / "out" / "metrics.json").read_text(encoding="utf-8"))
README = (ROOT / "README.md").read_text(encoding="utf-8")
BLOCK = README[README.index("<!-- mvp-metrics:start -->"):README.index("<!-- mvp-metrics:end -->")]


def frac(m):
    return f"{m['hits']}/{m['n']}"


def table_rows():
    rows = {}
    for line in BLOCK.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 3 and cells[0] not in ("Metric", "---"):
            rows[cells[0]] = (cells[1], cells[2])
    return rows


def test_results_table_matches_metrics():
    a, k, e = METRICS["anchor"], METRICS["keyword"], METRICS["external"]
    want = {
        "AUROC, test": (f"{k['test']['auroc']:.3f}", f"{a['test']['auroc']:.3f}"),
        "Detection, test": (frac(k["test"]["tpr"]), frac(a["test"]["tpr"])),
        "False blocks, clean pages": (frac(k["test"]["false_block_clean"]), frac(a["test"]["false_block_clean"])),
        "False blocks, hard negatives": (frac(k["test"]["false_block_hard_negative"]), frac(a["test"]["false_block_hard_negative"])),
        "Polite injection, no trigger words": (frac(k["test"]["per_style_tpr"]["polite_no_triggers"]),
                                               frac(a["test"]["per_style_tpr"]["polite_no_triggers"])),
        "Held-out Hindi/Hinglish injection": (frac(k["heldout"]["per_style_tpr"]["hindi_hinglish"]),
                                              frac(a["heldout"]["per_style_tpr"]["hindi_hinglish"])),
        "False blocks, benign Hindi insertions": (frac(k["heldout"]["false_block_benign_hindi"]),
                                                  frac(a["heldout"]["false_block_benign_hindi"])),
        "External: InjecAgent detection": (frac(e["keyword"]["tpr"]), frac(e["anchor"]["tpr"])),
        "External: InjecAgent false blocks": (frac(e["keyword"]["false_block"]), frac(e["anchor"]["false_block"])),
    }
    rows = table_rows()
    assert len(rows) == len(want)
    for prefix, values in want.items():
        match = [v for label, v in rows.items() if label.startswith(prefix)]
        assert match == [values], prefix


def test_prose_numbers_match_metrics():
    prose = BLOCK.split("<!-- mvp-metrics:end -->")[0].split("\n\n")[-1]
    assert f"AUROC {METRICS['shuffled_label_control']['test_auroc']:.3f}" in prose
    assert f"layer {METRICS['layer']} of 24" in prose
    assert f"{frac(METRICS['hijacked'])} injected demo scenarios" in prose
    assert f"AUROC {METRICS['external']['anchor']['auroc']:.3f}" in prose
    allowed = {f"{v:.3f}" for v in (METRICS["shuffled_label_control"]["test_auroc"], METRICS["external"]["anchor"]["auroc"])}
    assert set(re.findall(r"\b0\.\d+\b", prose)) <= allowed, "unsourced decimal in README prose"
    assert set(re.findall(r"\b\d+/\d+\b", prose)) <= {frac(METRICS["hijacked"])}, "unsourced count in README prose"


def test_readme_screenshot_exists():
    m = re.search(r"!\[[^\]]*\]\(([^)]+)\)", README[README.index("## MVP"):])
    assert m and (ROOT / m.group(1)).is_file()
