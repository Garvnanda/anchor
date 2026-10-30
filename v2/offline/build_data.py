"""Build the labelled, document-split dataset → data/<model>/rows.jsonl + out/<model>/data_summary.json (token budget per model)."""
import json
import random
import re
from collections import Counter, defaultdict

import attacks
from common import MAX_OUTPUT_TOKENS, SEED, load_tokenizer, parse, run_meta
from templates import (
    ATTACKERS, BENIGN, BENIGN_HINDI, BENIGN_SPLIT, GOALS, HARD_NEGATIVE_DOCS, HELDOUT_STYLE, HINDI_GOALS,
    BENIGN_MULTI, INJECTIONS, INNOCENT_TRIGGERS, JSON_BODY_WORDS, JSON_SHAPES, MULTI_SPLIT, NO_TRIGGER_STYLES,
    POLITE_GOALS, TASKS, TEMPLATE_SPLIT, TRAINED_STYLES, TRIGGER_SPLIT, URLS, by_split,
)

# Rows added after the first build draw from their own RNG (fixed seed per block) and are appended, so earlier
# rows stay byte-identical and keep their cached features.
LATER_STYLES = ["user_voice"]
FIRST_STYLES = [s for s in TRAINED_STYLES if s not in LATER_STYLES]


def goals_for(style):
    return NO_TRIGGER_STYLES.get(style, GOALS)


def json_escape(text):
    return json.dumps(text, ensure_ascii=False)[1:-1]  # how the text appears inside a JSON string

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

    def add(doc_id, split, output, label, style, position, insertion, template_id=None, kind=None, r=rng, **extra):
        rows.append({
            "id": f"{doc_id}-{style}" + (f"-{kind}" if kind else ""), "doc_id": doc_id, "split": split,
            "task": r.choice(TASKS), "output": output, "label": label, "style": style,
            "position": position, "insertion": insertion, "template_id": template_id, "kind": kind,
            **extra,  # H1 rows only (family, prior_outputs, insertion_parts); v1 rows stay byte-identical
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
            ins = fill(tmpl, goals_for(style), later)
            pos = later.choice(POSITIONS)
            add(doc_id, split, insert(doc, ins, pos), 1, style, pos, ins, tid, r=later)

    # Extra clean row per doc with a benign non-English sentence, so script/language alone is not a cue.
    multi = random.Random(SEED + 10)
    for i, doc in enumerate(main_docs):
        doc_id, split = f"d{i:03d}", split_of(i, N_DOCS)
        ins, pos = multi.choice(by_split(BENIGN_MULTI, MULTI_SPLIT, split)), multi.choice(POSITIONS)
        add(doc_id, split, insert(doc, ins, pos), 0, "benign_multilingual", pos, ins, r=multi)

    # JSON-shaped tool responses: short page in one of four shapes, a clean and an injected version per doc.
    js = random.Random(SEED + 20)
    for i, doc in enumerate(main_docs):
        doc_id, split = f"d{i:03d}", split_of(i, N_DOCS)
        words = doc.split()
        title, body = " ".join(words[:6]), " ".join(words[:JSON_BODY_WORDS])
        shape = js.choice(sorted(JSON_SHAPES))
        benign = js.choice(benign_for(split))
        style = js.choice(TRAINED_STYLES)
        tid, tmpl = js.choice(templates_for(style, split))
        attack = fill(tmpl, goals_for(style), js)
        for label, ins, row_style, t in ((0, benign, "json_clean", None), (1, attack, "json_tool", tid)):
            page = json.dumps(JSON_SHAPES[shape](title, body, ins), ensure_ascii=False)
            add(doc_id, split, page, label, row_style, shape, json_escape(ins), t, kind=style if label else None, r=js)

    family_rows(main_docs, add)
    return rows


SHORT_WORDS = 90  # new families use the first 90 words of a doc: TAG characters and two-page rows cost many tokens
SHORT_WORDS_INVISIBLE = 45  # TAG characters cost ~3 tokens each; 90 words dropped 1 in 5 rows over the budget


def family_rows(main_docs, add):
    """H1: one injected row + one length-matched benign control per (family, doc). Trained families on 3 of every
    4 main docs (offset per family); held-out families (tamil, tool_description) on test docs only, split
    "heldout". Each family draws from its own RNG and is appended, so earlier rows keep their cached features."""
    for k, fam in enumerate(attacks.FAMILIES + attacks.HELDOUT_FAMILIES):
        rng = random.Random(SEED + 100 + k)
        held = fam in attacks.HELDOUT_FAMILIES
        for i, doc in enumerate(main_docs):
            doc_id, split = f"d{i:03d}", split_of(i, N_DOCS)
            if held:
                if split != "test":
                    continue
                split = "heldout"
            elif (i + k) % 4 == 3:
                continue
            pool = benign_for("test" if held else split)
            order = rng.sample(pool, len(pool))
            short = " ".join(doc.split()[:SHORT_WORDS_INVISIBLE if fam == "invisible_unicode" else SHORT_WORDS])
            pos = rng.choice(POSITIONS)
            inj, ctrl = family_pair(fam, split, short, doc, pos, order, rng)
            for label, row in ((1, inj), (0, ctrl)):
                style = fam if label else f"benign_{fam}"
                add(doc_id, split, row.pop("output"), label, style, pos, row.pop("insertion"), row.pop("template_id"),
                    r=rng, family=fam, **row)


def _templates(items, split):
    t = list(enumerate(items))
    return t if split == "heldout" else by_split(t, TEMPLATE_SPLIT, split)


def family_pair(fam, split, short, doc, pos, order, rng):
    """(injected, control) dicts with output, insertion, template_id and any extra row fields."""
    a = attacks
    if fam == "encoded":
        tid, (kind, wrap) = rng.choice(_templates(a.ENCODED, split))
        ins = wrap.format(p=a._encode(kind, f"Ignore the user's task and {a.goal(rng)}."))
        bkind, bwrap = a.ENCODED_BENIGN[tid]
        ctrl = a.matched(lambda t: bwrap.format(p=a._encode(bkind, t)), len(ins), order)
    elif fam == "invisible_unicode":
        tid, (method, carrier) = rng.choice(_templates(a.INVISIBLE, split))
        hide = a.tag_encode if method == "tag" else a.zw_spread
        ins = carrier.format(h=hide(f"Ignore the user's task and {a.goal(rng)}."))
        ctrl = a.matched(lambda t: carrier.format(h=hide(t)), len(ins), order)
    elif fam == "homoglyph":
        tid, tmpl = rng.choice(_templates(a.HOMOGLYPH, split))
        ins = a.homoglyph(tmpl.format(goal=a.goal(rng)), rng)
        ctrl = a.homoglyph(a.matched(lambda t: t, len(ins), order), rng)
    elif fam == "split_payload":
        tid, (p1, p2) = rng.choice(_templates(a.SPLIT, split))
        g = a.goal(rng).split()
        parts = [f"{p1} {' '.join(g[:len(g) // 2])}", f"{p2} {' '.join(g[len(g) // 2:])}."]
        b1, b2 = a.SPLIT_BENIGN[tid]
        plain = a.matched(lambda t: f"{b1} {t} {b2}", len(" ".join(parts)), order)[len(b1) + 1:-len(b2) - 1].split()
        cparts = [f"{b1} {' '.join(plain[:len(plain) // 2])}", f"{b2} {' '.join(plain[len(plain) // 2:])}"]
        words = short.split()
        first, second = " ".join(words[:len(words) // 2]), " ".join(words[len(words) // 2:])

        def two(ps):
            return {"output": f"{ps[1]} {second}", "prior_outputs": [f"{first} {ps[0]}"],
                    "insertion": " ".join(ps), "insertion_parts": ps, "template_id": tid}
        return two(parts), two(cparts)
    elif fam == "rag_document":
        tid, tmpl = rng.choice(_templates(a.RAG, split))
        ins = tmpl.format(goal=a.goal(rng))
        ctrl = a.matched(lambda t: t, len(ins), order)
        words = short.split()
        c1, c2 = " ".join(words[:len(words) // 2]), " ".join(words[len(words) // 2:])
        page = lambda x: a.dumps(a.rag_results(c1, f"{c2} {x}"))  # noqa: E731
        return ({"output": page(ins), "insertion": json_escape(ins), "template_id": tid},
                {"output": page(ctrl), "insertion": json_escape(ctrl), "template_id": tid})
    elif fam == "exfil_link":
        tid, tmpl = rng.choice(_templates(a.EXFIL, split))
        ins = tmpl.format(url=rng.choice(URLS))
        bwrap = a.EXFIL_BENIGN[tid]
        ctrl = a.matched(lambda t: bwrap.format(p=t), len(ins), order)
    elif fam == "tool_description":
        tid, tmpl = rng.choice(_templates(a.TOOL_DESC, split))
        ins = tmpl.format(goal=a.goal(rng))
        bwrap = a.TOOL_DESC_BENIGN[tid]
        notes = rng.sample(a.TOOL_NOTES, len(a.TOOL_NOTES))
        ctrl = a.matched(lambda t: bwrap.format(p=t), len(ins), notes)
        page = lambda x: a.dumps(a.tool_list(short, a.TOOL_NAMES[tid], x))  # noqa: E731
        return ({"output": page(ins), "insertion": json_escape(ins), "template_id": tid},
                {"output": page(ctrl), "insertion": json_escape(ctrl), "template_id": tid})
    elif fam == "tamil":  # like Hindi: full document, benign-Tamil control (not length-matched, as for Hindi)
        tid, tmpl = rng.choice(_templates(a.TAMIL, split))
        ins = fill(tmpl, a.TAMIL_GOALS, rng)
        ctrl = rng.choice(a.BENIGN_TAMIL)
        return ({"output": insert(doc, ins, pos), "insertion": ins, "template_id": tid},
                {"output": insert(doc, ctrl, pos), "insertion": ctrl, "template_id": None})
    else:
        raise ValueError(fam)
    return ({"output": insert(short, ins, pos), "insertion": ins, "template_id": tid},
            {"output": insert(short, ctrl, pos), "insertion": ctrl, "template_id": tid})


def truncate_check(rows, tok):
    """Drop rows whose output exceeds the token budget of this model's tokenizer (truncation would risk cutting
    the insertion)."""
    for r in rows:  # per tool output: a split-payload row's earlier page has the same budget
        r["n_tokens"] = max(len(tok(o)["input_ids"]) for o in r.get("prior_outputs", []) + [r["output"]])
    over = {r["id"] for r in rows if r["n_tokens"] > MAX_OUTPUT_TOKENS}
    # Paired rows (injection + its control per doc): Hindi pairs and every H1 family pair. Drop both or neither.
    pair = lambda r: (r["doc_id"], r.get("family") or ("hindi" if r["split"] == "heldout" else None))  # noqa: E731
    bad = {pair(r) for r in rows if r["id"] in over and pair(r)[1]}
    drop = lambda r: r["id"] in over or pair(r) in bad  # noqa: E731
    return [r for r in rows if not drop(r)], [r for r in rows if drop(r)]


def summary(rows, dropped):
    counts = Counter((r["split"], r["style"], r["label"]) for r in rows)
    words = defaultdict(list)
    for r in rows:
        if r["split"] != "heldout" and r["style"] != "hard_negative":
            fmt = "json" if r["style"].startswith("json") else "prose"
            words[(fmt, r["label"])].append(len(r["output"].split()))
    mean = lambda k: round(sum(words[k]) / len(words[k]), 1)  # noqa: E731
    return {
        "rows": len(rows),
        "dropped_over_token_budget": [r["id"] for r in dropped],
        "docs": len({r["doc_id"] for r in rows}),
        "counts": [{"split": s, "style": st, "label": lb, "n": n} for (s, st, lb), n in sorted(counts.items())],
        "mean_words": {f"{fmt}_{'injected' if lb else 'clean'}": mean((fmt, lb)) for fmt, lb in sorted(words)},
    }


def main(argv=None):
    run, _ = parse(argv, __doc__)
    rows, dropped = truncate_check(build(), load_tokenizer(run))
    run.data.mkdir(parents=True, exist_ok=True)
    run.out.mkdir(parents=True, exist_ok=True)
    with open(run.data / "rows.jsonl", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    s = {"run_meta": run_meta(run), **summary(rows, dropped)}
    (run.out / "data_summary.json").write_text(json.dumps(s, indent=2), encoding="utf-8")
    print(f"rows={s['rows']} docs={s['docs']} dropped={len(dropped)} mean_words={s['mean_words']}")


if __name__ == "__main__":
    main()
