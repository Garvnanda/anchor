"""Design mock: every colour family ships a light and a dark token set."""
import re
from pathlib import Path

MOCK = Path(__file__).resolve().parents[2] / "design" / "mock.html"
FAMILIES = ["sage", "ops", "ink"]
REQUIRED = ["--bg", "--panel", "--line", "--text", "--muted", "--accent", "--safe", "--leak", "--warn", "--amber"]


def _blocks(css):
    """Map (family, mode) -> declared custom properties. Bare :root is the ops-dark default."""
    out = {}
    for sel, body in re.findall(r"(:root[^{]*)\{([^}]*)\}", css):
        props = set(re.findall(r"(--[\w-]+)\s*:", body))
        fam = re.search(r'data-family="(\w+)"', sel)
        mode = re.search(r'data-mode="(\w+)"', sel)
        if fam and mode:
            out[(fam.group(1), mode.group(1))] = props
        elif sel.strip() == ":root":
            out[("ops", "dark")] = props
    return out


def test_every_family_has_light_and_dark():
    blocks = _blocks(MOCK.read_text(encoding="utf-8"))
    for fam in FAMILIES:
        for mode in ("light", "dark"):
            assert (fam, mode) in blocks, f"missing {fam}/{mode}"


def test_colour_sets_are_complete():
    blocks = _blocks(MOCK.read_text(encoding="utf-8"))
    for key, props in blocks.items():
        missing = [p for p in REQUIRED if p not in props]
        assert not missing, f"{key} missing {missing}"


def test_mode_switch_offers_auto_light_dark():
    html = MOCK.read_text(encoding="utf-8")
    for m in ("auto", "light", "dark"):
        assert f'data-m="{m}"' in html
    assert "prefers-color-scheme: dark" in html
