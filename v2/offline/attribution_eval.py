"""H4: choose the playground's attribution method by measurement → out/<model>/attribution.json.

On N injected val rows (single page, insertion known): leave-one-sentence-out (one pass per sentence, the
reference) vs projection (one pass: per-token states on the probe direction). Measured: how often each method's
top sentence overlaps the inserted text, and how often the two methods pick the same top sentence. The cheap
method ships only if it agrees (technical.md 1.3): top-1 agreement >= AGREE and insertion hit rate no more than
MAX_GAP below leave-one-out's. Otherwise the playground shows no live attribution.
"""
import json
import random

from common import SEED, parse, run_meta

N_ROWS = 50
AGREE, MAX_GAP = 0.6, 0.10


def top(spans):
    return max(spans, key=lambda a: a["weight"]) if spans else None


def hits_insertion(span, r):
    at = r["output"].find(r["insertion"])
    return span is not None and at >= 0 and span["start"] < at + len(r["insertion"]) and at < span["end"]


def main(argv=None):
    run, _ = parse(argv, __doc__)
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from anchor.scorer import Scorer

    rows = [json.loads(line) for line in (run.data / "rows.jsonl").read_text(encoding="utf-8").splitlines()]
    pool = [r for r in rows if r["split"] == "val" and r["label"] == 1 and not r.get("prior_outputs")
            and r["insertion"] and r["insertion"] in r["output"]]
    sample = random.Random(SEED).sample(pool, min(N_ROWS, len(pool)))
    scorer = Scorer(run)
    per_row = []
    for i, r in enumerate(sample, 1):
        loo = scorer.leave_one_out(r["task"], r["output"])
        proj = scorer.projection(r["task"], r["output"])
        tl, tp = top(loo), top(proj)
        per_row.append({"id": r["id"], "loo_hits": hits_insertion(tl, r), "projection_hits": hits_insertion(tp, r),
                        "same_top": tl is not None and tp is not None and (tl["start"], tl["end"]) == (tp["start"], tp["end"])})
        print(i, per_row[-1], flush=True)
    n = len(per_row)
    rate = lambda k: round(sum(p[k] for p in per_row) / n, 4)  # noqa: E731
    res = {"run_meta": run_meta(run, scorer.device), "n_rows": n,
           "loo_insertion_hit": rate("loo_hits"), "projection_insertion_hit": rate("projection_hits"),
           "top1_agreement": rate("same_top"), "rule": {"agree_at_least": AGREE, "max_gap": MAX_GAP}, "rows": per_row}
    ok = res["top1_agreement"] >= AGREE and res["projection_insertion_hit"] >= res["loo_insertion_hit"] - MAX_GAP
    res["chosen"] = "projection" if ok else "none"
    (run.out / "attribution.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    print({k: res[k] for k in ("n_rows", "loo_insertion_hit", "projection_insertion_hit", "top1_agreement", "chosen")})


if __name__ == "__main__":
    main()
