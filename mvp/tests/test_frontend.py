"""Phase 4: static checks on the vanilla frontend (browser behaviour itself: tests/browser_check.js)."""
import re
from pathlib import Path

PUBLIC = Path(__file__).resolve().parents[1] / "public"
APP = (PUBLIC / "app.js").read_text(encoding="utf-8")
CSS = (PUBLIC / "style.css").read_text(encoding="utf-8")


def test_val_threshold_sent_unrounded_on_load_and_reset():
    """The default run must use the exact val-chosen threshold, not the slider's 0.001 rounding."""
    assert APP.count("setThreshold(health.threshold, true)") == 1
    assert APP.count("setThreshold(state.health.threshold, true)") == 1
    assert "state.threshold = exact ? v : Math.round(v * 1000) / 1000" in APP


def test_heldout_cards_still_say_injected_or_clean():
    tags = APP[APP.index("function labelTags"):APP.index("function renderPicker")]
    assert '"injected" : "clean"' in tags and '"held-out"' in tags
    assert "return tags" in tags and "if (s.split === \"heldout\") tags.push" in tags


def test_page_text_never_inserted_as_html():
    assert not re.search(r"innerHTML|outerHTML|insertAdjacentHTML|document\.write|eval\(", APP)


def test_theme_follows_system_with_manual_override():
    assert "@media (prefers-color-scheme: dark)" in CSS
    assert ':root:not([data-theme="light"])' in CSS and ':root[data-theme="dark"]' in CSS
    assert 'localStorage.setItem("anchor-theme"' in APP


def test_every_number_comes_from_the_api():
    """No hand-typed scores: the UI reads only /api/*."""
    assert set(re.findall(r'api\("(/api/[a-z]+)"', APP)) == {"/api/health", "/api/scenarios", "/api/metrics", "/api/run"}
    assert not re.search(r"\b0\.\d{3,}\b", APP)  # no literal probe scores / thresholds


def test_hard_negative_cards_name_their_style():
    """§5.2: each card is tagged with its style; hard negatives also show their kind."""
    assert 's.style === "hard_negative" ? `hard_negative · ${s.kind}`' in APP


def test_reset_does_nothing_without_health():
    assert 'if (!state.health) return;' in APP[APP.index('$("#reset")'):]


def test_favicon_declared():
    assert 'rel="icon"' in (PUBLIC / "index.html").read_text(encoding="utf-8")
