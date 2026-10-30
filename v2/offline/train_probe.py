"""Probe per layer, layer + threshold on val, metrics on test/heldout vs keyword baseline → out/<model>/."""
import json
from datetime import date

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler

from common import SEED, check_run_meta, parse, run_meta
from templates import TRAINED_STYLES, keyword_hit

TARGET_FPR = 0.05
N_SHUFFLES = 30


def fit(X, y):
    scaler = StandardScaler().fit(X)
    clf = LogisticRegression(C=0.1, max_iter=2000).fit(scaler.transform(X), y)
    return scaler, clf


def predict(scaler, clf, X):
    return clf.predict_proba(scaler.transform(X))[:, 1]


def threshold_at_fpr(scores, labels, fpr):
    """Smallest threshold whose false-positive rate on these labels is ≤ fpr (block when score ≥ t)."""
    neg = np.sort(scores[labels == 0])
    for t in np.unique(scores):
        if (neg >= t).mean() <= fpr:
            return float(t)
    return float(scores.max()) + 1e-6


def rate(hits, n):
    return {"rate": round(hits / n, 4) if n else None, "hits": int(hits), "n": int(n)}


def auroc(labels, scores):
    return round(float(roc_auc_score(labels, scores)), 4) if len(set(labels)) == 2 else None


def evaluate(rows, idx, scores, blocked):
    """Detection metrics on one split. `blocked` = boolean decision per row."""
    lab = np.array([rows[i]["label"] for i in idx])
    sty = [rows[i]["style"] for i in idx]
    sc, bl = scores[idx], blocked[idx]
    out = {"auroc": auroc(lab, sc), "tpr": rate(bl[lab == 1].sum(), (lab == 1).sum())}
    for name in ("clean", "benign_multilingual", "json_clean", "hard_negative", "benign_hindi"):
        m = np.array([s == name for s in sty])
        if m.any():
            out[f"false_block_{name}"] = rate(bl[m].sum(), m.sum())
    hard = [i for i in idx if rows[i]["style"] == "hard_negative"]  # injected json_tool rows carry a kind too
    kinds = sorted({rows[i]["kind"] for i in hard if rows[i]["kind"]})
    if kinds:  # hand-written hard negatives are shorter than SQuAD ones; report both so a length cue shows up
        out["false_block_hard_negative_by_kind"] = {}
        for kind in kinds:
            m = np.array([rows[i]["style"] == "hard_negative" and rows[i]["kind"] == kind for i in idx])
            out["false_block_hard_negative_by_kind"][kind] = rate(bl[m].sum(), m.sum())
    out["per_style_tpr"] = {}
    for name in TRAINED_STYLES + ["json_tool", "hindi_hinglish"]:
        m = np.array([s == name for s in sty])
        if m.any():
            out["per_style_tpr"][name] = rate(bl[m].sum(), m.sum())
    return out


def main(argv=None):
    run, _ = parse(argv, __doc__)
    rows = [json.loads(line) for line in (run.data / "rows.jsonl").read_text(encoding="utf-8").splitlines()]
    assert json.loads((run.features / "ids.json").read_text()) == [r["id"] for r in rows]
    feature_meta = json.loads((run.features / "meta.json").read_text())
    check_run_meta(feature_meta, run, "features")
    meta = run_meta(run, feature_meta["device"])  # the features' device: that is where the activations came from
    y = np.array([r["label"] for r in rows])
    split = np.array([r["split"] for r in rows])
    tr, va, te, ho = (np.where(split == s)[0] for s in ("train", "val", "test", "heldout"))

    sweep, models = [], {}
    for L in run.layers:
        X = np.load(run.features / f"delta_L{L}.npy")
        scaler, clf = fit(X[tr], y[tr])
        models[L] = (X, scaler, clf)
        sweep.append({"layer": L, "val_auroc": auroc(y[va], predict(scaler, clf, X[va]))})
    best = max(sweep, key=lambda s: s["val_auroc"])["layer"]
    X, scaler, clf = models[best]
    # Round once: threshold, decisions and every stored score use the same 6-decimal values.
    scores = np.round(predict(scaler, clf, X), 6)
    thr = threshold_at_fpr(scores[va], y[va], TARGET_FPR)

    # Keyword baseline on the same rows; fixed rule, no tuning.
    kw = np.array([keyword_hit(r["output"]) for r in rows])

    # Shuffled-label control: same probe, train labels permuted, evaluated on real test labels.
    # Averaged over N_SHUFFLES permutations so the gate does not hinge on one lucky draw.
    rng = np.random.default_rng(SEED)
    shuffled = []
    for _ in range(N_SHUFFLES):
        s_scaler, s_clf = fit(X[tr], rng.permutation(y[tr]))
        shuffled.append(auroc(y[te], predict(s_scaler, s_clf, X[te])))
    shuffled_auroc = round(float(np.mean(shuffled)), 4)

    anchor_block, kw_block = scores >= thr, kw
    metrics = {
        "run_meta": meta, "model": run.hf_id, "layer": best, "threshold": round(thr, 6), "target_fpr": TARGET_FPR,
        "built_at": date.today().isoformat(),
        "rows": {s: int((split == s).sum()) for s in ("train", "val", "test", "heldout")},
        "anchor": {"val_fpr": rate(anchor_block[va][y[va] == 0].sum(), (y[va] == 0).sum()),
                   "test": evaluate(rows, te, scores, anchor_block),
                   "heldout": evaluate(rows, ho, scores, anchor_block)},
        "keyword": {"test": evaluate(rows, te, kw.astype(float), kw_block),
                    "heldout": evaluate(rows, ho, kw.astype(float), kw_block)},
        "shuffled_label_control": {"test_auroc": shuffled_auroc, "sd": round(float(np.std(shuffled)), 4),
                                   "min": min(shuffled), "max": max(shuffled), "n_permutations": N_SHUFFLES},
    }
    a, k = metrics["anchor"]["test"], metrics["keyword"]["test"]
    metrics["verdict"] = (
        f"probe {'beats' if a['auroc'] > k['auroc'] else 'ties' if a['auroc'] == k['auroc'] else 'loses to'} "
        f"keyword on test AUROC ({a['auroc']} vs {k['auroc']}); "
        f"TPR {a['tpr']['hits']}/{a['tpr']['n']} vs {k['tpr']['hits']}/{k['tpr']['n']}"
    )

    probe = {"run_meta": meta, "model": run.hf_id, "layer": best, "threshold": thr, "mean": scaler.mean_.tolist(),
             "scale": scaler.scale_.tolist(), "coef": clf.coef_[0].tolist(), "intercept": float(clf.intercept_[0])}
    run.out.mkdir(parents=True, exist_ok=True)
    (run.out / "probe.json").write_text(json.dumps(probe))
    (run.out / "layer_sweep.json").write_text(json.dumps({"run_meta": meta, "sweep": sweep}, indent=2))
    (run.out / "metrics.json").write_text(json.dumps(metrics, indent=2))
    (run.out / "scores.json").write_text(json.dumps({"run_meta": meta, "scores": {
        r["id"]: {"probe_score": round(float(scores[i]), 6), "keyword_hit": bool(kw[i]), "split": r["split"]}
        for i, r in enumerate(rows)}}, indent=1))
    print(json.dumps(sweep))
    print(metrics["verdict"], "| shuffled AUROC", shuffled_auroc, "| threshold", round(thr, 4))


if __name__ == "__main__":
    main()
