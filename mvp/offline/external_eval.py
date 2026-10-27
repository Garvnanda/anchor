"""Phase 2: frozen probe + frozen threshold on an external benchmark (InjecAgent, MIT).

Never used for training, layer choice or threshold. Injected rows: InjecAgent base-setting tool responses
(attacker instruction embedded, no "IGNORE ALL" prefix). Clean rows: the same tool-response templates with
the attacker slot filled by a neutral sentence.
"""
import json
import random
import urllib.request

import numpy as np
import torch

from common import DATA, OUT, SEED, load_model, prompt_ids, tool_call
from templates import keyword_hit

BASE_URL = "https://raw.githubusercontent.com/uiuc-kang-lab/InjecAgent/main/data/"
FILES = ["test_cases_dh_base.json", "test_cases_ds_base.json"]
EXT = DATA / "external"
N_INJECTED = 200
SLOT = "<Attacker Instruction>"

# Neutral fillers for the attacker slot (reviews, notes, emails, events, messages).
NEUTRAL = [
    "Works as described and arrived on time.",
    "Thanks, see you at the meeting on Thursday.",
    "Reminder: the quarterly report is due next week.",
    "Great battery life, a little heavy for travel.",
    "Running about ten minutes late, start without me.",
    "The photos from the weekend trip are in the shared folder.",
]


def load_cases():
    EXT.mkdir(parents=True, exist_ok=True)
    cases = []
    for f in FILES:
        path = EXT / f
        if not path.exists():
            urllib.request.urlretrieve(BASE_URL + f, path)
        cases += json.loads(path.read_text(encoding="utf-8"))
    return cases


def build_rows(cases):
    rng = random.Random(SEED)
    injected = rng.sample(cases, min(N_INJECTED, len(cases)))
    rows = [{"task": c["User Instruction"], "tool": c["User Tool"], "args": c["Tool Parameters"],
             "output": c["Tool Response"].strip('"'), "label": 1} for c in injected]
    seen = {}
    for c in cases:  # one clean row per distinct (user tool, template) × neutral filler
        key = (c["User Tool"], c["Tool Response Template"])
        if key not in seen and SLOT in c["Tool Response Template"]:
            seen[key] = c
    for c in seen.values():
        for filler in NEUTRAL:
            rows.append({"task": c["User Instruction"], "tool": c["User Tool"], "args": c["Tool Parameters"],
                         "output": c["Tool Response Template"].replace(SLOT, filler), "label": 0})
    return rows


def main():
    probe = json.loads((OUT / "probe.json").read_text())
    L, thr = probe["layer"], probe["threshold"]
    mean, scale = np.array(probe["mean"]), np.array(probe["scale"])
    coef, b = np.array(probe["coef"]), probe["intercept"]

    rows = build_rows(load_cases())
    tok, model = load_model()

    def state(task, output=None, call=None):
        ids = prompt_ids(tok, task, output, call) if output is not None else prompt_ids(tok, task)
        with torch.no_grad():
            return model(ids, output_hidden_states=True).hidden_states[L][0, -1].float().numpy()

    base, scores = {}, []
    for r in rows:
        args = r["args"] if isinstance(r["args"], dict) else {"input": str(r["args"])}
        if r["task"] not in base:
            base[r["task"]] = state(r["task"])
        delta = state(r["task"], r["output"], tool_call(r["tool"], args)) - base[r["task"]]
        z = ((delta - mean) / scale) @ coef + b
        scores.append(round(float(1 / (1 + np.exp(-z))), 6))  # same rounding as train_probe

    y = np.array([r["label"] for r in rows])
    s = np.array(scores)
    kw = np.array([keyword_hit(r["output"]) for r in rows])

    def block(mask):
        return {"tpr": {"hits": int(mask[y == 1].sum()), "n": int((y == 1).sum()),
                        "rate": round(float(mask[y == 1].mean()), 4)},
                "false_block": {"hits": int(mask[y == 0].sum()), "n": int((y == 0).sum()),
                                "rate": round(float(mask[y == 0].mean()), 4)}}

    from sklearn.metrics import roc_auc_score
    ext = {"source": "InjecAgent (uiuc-kang-lab/InjecAgent, MIT), base setting",
           "anchor": {"auroc": round(float(roc_auc_score(y, s)), 4), **block(s >= thr)},
           "keyword": block(kw)}
    m = json.loads((OUT / "metrics.json").read_text())
    m["external"] = ext
    (OUT / "metrics.json").write_text(json.dumps(m, indent=2))
    (OUT / "external_scores.json").write_text(json.dumps(
        [{"label": r["label"], "tool": r["tool"], "probe_score": round(sc, 6), "keyword_hit": bool(k)}
         for r, sc, k in zip(rows, scores, kw)], indent=1))
    print(json.dumps(ext, indent=2))


if __name__ == "__main__":
    main()
