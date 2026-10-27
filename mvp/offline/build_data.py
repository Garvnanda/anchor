"""Phase 1: build the labelled, document-split dataset → data/rows.jsonl + out/data_summary.json."""
import json
import random
import re
from collections import Counter, defaultdict

from common import DATA, MAX_OUTPUT_TOKENS, MODEL, OUT, SEED
from templates import (
    ATTACKERS, BENIGN, BENIGN_HINDI, BENIGN_SPLIT, GOALS, HARD_NEGATIVE_DOCS, HELDOUT_STYLE, HINDI_GOALS,
    INJECTIONS, INNOCENT_TRIGGERS, NO_TRIGGER_STYLES, POLITE_GOALS, TASKS, TEMPLATE_SPLIT, TRAINED_STYLES,
    TRIGGER_SPLIT, URLS, by_split,
)

# Styles added after the first build draw from their own RNG and are appended, so earlier rows stay
# byte-identical and keep their cached features.
LATER_STYLES = ["user_voice"]
FIRST_STYLES = [s for s in TRAINED_STYLES if s not in LATER_STYLES]

N_DOCS = 150
N_SQUAD_HARD_NEG = 20
MIN_WORDS, MAX_WORDS = 80, 250
POSITIONS = ["start", "middle", "end"]


def load_paragraphs(n):
    from datasets import load_dataset

    seen, paras = set(), []
    for ctx in load_dataset("rajpurkar/squad", split="validation")["context"]:
        ctx = " ".join(ctx.split())
        if ctx in seen or not MIN_WORDS <= len(ctx.split()) <= MAX_WORDS:
            continue
        seen.add(ctx)
        paras.append(ctx)
    random.Random(SEED).shuffle(paras)
    assert len(paras) >= n, f"only {len(paras)} usable paragraphs"
    return paras[:n]


def insert(doc, text, position):
    sents = re.split(r"(?<=[.!?])\s+", doc)
    at = {"start": 0, "middle": len(sents) // 2, "end": len(sents)}[position]
    return " ".join(sents[:at] + [text] + sents[at:])


def split_of(i, n):
    """70/15/15 by index over a shuffled list."""
    if i < round(n * 0.70):
        return "train"
    return "val" if i < round(n * 0.85) else "test"


def fill(template, goals, rng):
    goal = rng.choice(goals).format(addr=rng.choice(ATTACKERS), url=rng.choice(URLS))
    return template.format(goal=goal)


def templates_for(style, split):
    t = list(enumerate(INJECTIONS[style]))
    if style == HELDOUT_STYLE:
        return t  # never trained or tuned on; all templates are unseen
    return by_split(t, TEMPLATE_SPLIT, split)


def benign_for(split):
    return by_split(BENIGN, BENIGN_SPLIT, split)


def build():
    rng = random.Random(SEED)
    paras = load_paragraphs(N_DOCS + N_SQUAD_HARD_NEG)
    main_docs, hn_squad = paras[:N_DOCS], paras[N_DOCS:]
    rows = []

    def add(doc_id, split, output, label, style, position, insertion, template_id=None, kind=None, r=rng):
        rows.append({
            "id": f"{doc_id}-{style}" + (f"-{kind}" if kind else ""), "doc_id": doc_id, "split": split,
            "task": r.choice(TASKS), "output": output, "label": label, "style": style,
            "position": position, "insertion": insertion, "template_id": template_id, "kind": kind,
        })

    # Main documents: one clean row with a benign insertion + one row per trained injection style.
    for i, doc in enumerate(main_docs):
        doc_id, split = f"d{i:03d}", split_of(i, N_DOCS)
        pos = rng.choice(POSITIONS)
        ins = rng.choice(benign_for(split))
        add(doc_id, split, insert(doc, ins, pos), 0, "clean", pos, ins)
        for style in FIRST_STYLES:
            tid, tmpl = rng.choice(templates_for(style, split))
            ins = fill(tmpl, POLITE_GOALS if style == "polite_no_triggers" else GOALS, rng)
            pos = rng.choice(POSITIONS)
            add(doc_id, split, insert(doc, ins, pos), 1, style, pos, ins, tid)
        if split == "test":  # held-out style, built from test documents only, with a benign-Hindi control
            tid, tmpl = rng.choice(templates_for(HELDOUT_STYLE, split))
            ins = fill(tmpl, HINDI_GOALS, rng)
            pos = rng.choice(POSITIONS)
            add(doc_id, "heldout", insert(doc, ins, pos), 1, HELDOUT_STYLE, pos, ins, tid)
            ins = rng.choice(BENIGN_HINDI)
            pos = rng.choice(POSITIONS)
            add(doc_id, "heldout", insert(doc, ins, pos), 0, "benign_hindi", pos, ins)

    # Hard negatives: their own documents, split per kind so each split gets each kind.
    by_kind = defaultdict(list)
    for kind, text in HARD_NEGATIVE_DOCS:
        by_kind[kind].append(text)
    k = 0
    for kind, docs in by_kind.items():  # hand-written: last doc → test, second-last → val, rest → train
        n = len(docs)
        for j, doc in enumerate(docs):
            split = "test" if j == n - 1 else "val" if j == n - 2 else "train"
            add(f"h{k:03d}", split, doc, 0, "hard_negative", None, None, kind=kind)
            k += 1
    for j, doc in enumerate(hn_squad):  # SQuAD docs + an innocent trigger sentence from this split's own pool
        split = split_of(j, len(hn_squad))
        ins, pos = rng.choice(by_split(INNOCENT_TRIGGERS, TRIGGER_SPLIT, split)), rng.choice(POSITIONS)
        add(f"h{k:03d}", split, insert(doc, ins, pos), 0, "hard_negative", pos, ins, kind="squad_trigger")
        k += 1

    for n, style in enumerate(LATER_STYLES, 1):
        later = random.Random(SEED + n)
        for i, doc in enumerate(main_docs):
            doc_id, split = f"d{i:03d}", split_of(i, N_DOCS)
            tid, tmpl = later.choice(templates_for(style, split))
            ins = fill(tmpl, NO_TRIGGER_STYLES[style], later)
            pos = later.choice(POSITIONS)
            add(doc_id, split, insert(doc, ins, pos), 1, style, pos, ins, tid, r=later)
    return rows


def truncate_check(rows):
    """Drop rows whose output exceeds the token budget (truncation would risk cutting the insertion)."""
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(MODEL)
    for r in rows:
        r["n_tokens"] = len(tok(r["output"])["input_ids"])
    over = {r["id"] for r in rows if r["n_tokens"] > MAX_OUTPUT_TOKENS}
    # Held-out rows come in pairs (Hindi injection + benign-Hindi control per doc): drop both or neither.
    pair_docs = {r["doc_id"] for r in rows if r["split"] == "heldout" and r["id"] in over}
    drop = lambda r: r["id"] in over or (r["split"] == "heldout" and r["doc_id"] in pair_docs)  # noqa: E731
    return [r for r in rows if not drop(r)], [r for r in rows if drop(r)]


def summary(rows, dropped):
    counts = Counter((r["split"], r["style"], r["label"]) for r in rows)
    words = defaultdict(list)
    for r in rows:
        if r["split"] != "heldout" and r["style"] != "hard_negative":
            words[r["label"]].append(len(r["output"].split()))
    return {
        "rows": len(rows),
        "dropped_over_token_budget": [r["id"] for r in dropped],
        "docs": len({r["doc_id"] for r in rows}),
        "counts": [{"split": s, "style": st, "label": lb, "n": n} for (s, st, lb), n in sorted(counts.items())],
        "mean_words": {"clean": round(sum(words[0]) / len(words[0]), 1),
                       "injected": round(sum(words[1]) / len(words[1]), 1)},
    }


def main():
    rows, dropped = truncate_check(build())
    DATA.mkdir(exist_ok=True)
    OUT.mkdir(exist_ok=True)
    with open(DATA / "rows.jsonl", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    s = summary(rows, dropped)
    (OUT / "data_summary.json").write_text(json.dumps(s, indent=2), encoding="utf-8")
    print(f"rows={s['rows']} docs={s['docs']} dropped={len(dropped)} mean_words={s['mean_words']}")


if __name__ == "__main__":
    main()
