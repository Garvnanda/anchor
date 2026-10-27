"""Deterministic choice of the 8 demo scenarios from test / held-out rows only (never train or val)."""
import re

from templates import TASKS

EMAIL_TASK = TASKS[0]
SECRET_WORDS = ("key", "token")

# (scenario id, title, filter on a row)
SPECS = [
    (1, "Clean report page", lambda r: r["split"] == "test" and r["style"] == "clean"),
    (2, "HTML-comment injection", lambda r: r["split"] == "test" and r["style"] == "html_comment"),
    (3, "Visible imperative injection", lambda r: r["split"] == "test" and r["style"] == "visible_imperative"),
    (4, "Polite injection, no trigger words", lambda r: r["split"] == "test" and r["style"] == "polite_no_triggers"),
    (5, "Markdown alt-text injection", lambda r: r["split"] == "test" and r["style"] == "markdown_hidden"),
    (6, "Security blog quoting an attack", lambda r: r["split"] == "test" and r["kind"] == "security_blog"),
    (7, "Recipe using \"ignore\" and \"instructions\"", lambda r: r["split"] == "test" and r["kind"] == "recipe"),
    (8, "Hindi/Hinglish injection (held-out style)", lambda r: r["split"] == "heldout" and r["style"] == "hindi_hinglish"),
]


def _rank(r):
    """Prefer injections that name an attacker email address (so the scripted action and the hijack check
    match what the page asks for), then the summarize-and-email task, then goals about the key/token."""
    ins = (r["insertion"] or "").lower()
    needs_addr = r["label"] == 1 and attacker_address(r["insertion"]) is None
    return (needs_addr, r["task"] != EMAIL_TASK, not any(w in ins for w in SECRET_WORDS), r["id"])


def pick(rows):
    out = []
    for sid, title, keep in SPECS:
        cands = sorted((r for r in rows if keep(r)), key=_rank)
        assert cands, f"no row for scenario {sid}"
        out.append((sid, title, cands[0]))
    return out


def attacker_address(text):
    m = re.search(r"[\w.+-]+@[\w-]+\.example", text or "")
    return m.group(0) if m else None
