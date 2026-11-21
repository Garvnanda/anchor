"""H3: rebuild the AgentDojo, tau-bench and BIPIA tool-output sets with lzwhehe/benign-instruction-bench (MIT),
steps 1-3 of its reproduce.sh minus the general corpus, CPU only, PYTHONHASHSEED=0 (its own requirement),
PYTHONUTF8=1 (Windows: its scripts open files with the default encoding), and the AgentDojo steps run through
frozen_clock.py: AgentDojo's write tools stamp outputs with the wall clock, which made the differential labels and
the file hashes change from run to run (decisions.md 2026-10-30).

  python agentbench_sets.py            rebuild into data/agentbench/, write out/agentbench_sets.json
  python agentbench_sets.py --check    rebuild a second time into a temp folder; hashes must be identical

Sets are evaluation-only: never used for training, layer, position or threshold choice (`assert_eval_only`, used
by G3). They are rebuilt, not redistributed, so data/agentbench/ is git-ignored; only counts and hashes are committed.
Needs (one-time, outside the repo): the benchmark repo at $BIB_DIR (default ~/tools/bib), BIPIA / tau-bench /
InjecAgent clones in ~/agentsec/, and a Python with agentdojo==0.1.34 at $AGENTDOJO_PY.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

from common import DATA_ROOT, OUT_ROOT

HOME = Path.home()
BIB = Path(os.environ.get("BIB_DIR", HOME / "tools" / "bib"))
AGENTSEC = HOME / "agentsec"
AGENTDOJO_PY = Path(os.environ.get("AGENTDOJO_PY", HOME / "tools" / "agentdojo-venv" / "Scripts" / "python.exe"))
WORK = DATA_ROOT / "agentbench"
OUT = OUT_ROOT / "agentbench_sets.json"

# (set name, file, benchmark): benign-only replay + three matched sets, as in the paper's Table 2.
SETS = [("agentdojo_benign", "agentdojo_benign_outputs.jsonl", "AgentDojo v1.2"),
        ("agentdojo_pairs", "agentdojo_pairs.jsonl", "AgentDojo v1.2"),
        ("bipia_pairs", "bipia_pairs.jsonl", "BIPIA"),
        ("taubench_eval", "taubench_eval.jsonl", "tau-bench")]
# The paper's stored label vectors for the same sets (results/normalized_probs_*.json): our rebuild must equal them.
PAPER_LABELS = {"agentdojo_pairs": "normalized_probs_main.json", "bipia_pairs": "normalized_probs_bipia.json"}
SOURCES = {"benign-instruction-bench": BIB, "BIPIA": AGENTSEC / "BIPIA", "tau-bench": AGENTSEC / "tau-bench",
           "InjecAgent": AGENTSEC / "InjecAgent"}


FROZEN_CLOCK = Path(__file__).resolve().with_name("frozen_clock.py")
WRITE_TOOLS = {"send_email", "create_file", "append_to_file", "share_file"}  # the tools that read the clock


def steps():
    s, py = BIB / "scripts", sys.executable
    ad = [str(AGENTDOJO_PY), FROZEN_CLOCK]
    return [[*ad, s / "collect_agentdojo_outputs.py"],
            [*ad, s / "collect_agentdojo_pairs.py", "important_instructions,ignore_previous,direct", "agentdojo_pairs.jsonl"],
            [*ad, s / "attach_requests.py", "agentdojo_pairs.jsonl"],
            [*ad, s / "attach_requests.py", "agentdojo_benign_outputs.jsonl"],
            [py, s / "build_bipia.py"],
            [py, s / "collect_taubench.py"],
            [py, s / "build_taubench_eval.py"]]


def rebuild(work):
    work.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "PYTHONHASHSEED": "0", "PYTHONUTF8": "1"}
    for cmd in steps():
        subprocess.run([str(c) for c in cmd], cwd=work, env=env, check=True, stdout=subprocess.DEVNULL)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def label(r):
    return int(r.get("label", 0))  # the benign replay has no label field: every row is benign


def commit(path):
    try:
        return subprocess.run(["git", "-C", str(path), "rev-parse", "HEAD"], capture_output=True, text=True,
                              check=True).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def summarize(work):
    out = {"built_at": date.today().isoformat(), "env": {"PYTHONHASHSEED": "0", "PYTHONUTF8": "1"},
           "agentdojo": _agentdojo_version(), "sources": {k: commit(v) for k, v in SOURCES.items()},
           "use": "evaluation only: never training, layer, position or threshold choice", "sets": {}}
    for name, fname, bench in SETS:
        rows = load(work / fname)
        labels = [label(r) for r in rows]
        entry = {"file": fname, "benchmark": bench, "rows": len(rows), "injected": sum(labels),
                 "benign": len(labels) - sum(labels), "sha256": sha256(work / fname)}
        if name in PAPER_LABELS:
            paper = [int(x) for x in json.loads((BIB / "results" / PAPER_LABELS[name]).read_text(encoding="utf-8"))["labels"]]
            only_paper = [i for i, (a, b) in enumerate(zip(paper, labels)) if a == 1 and b == 0]
            entry["vs_paper"] = {
                "same_rows": len(paper) == len(labels), "labels_equal": paper == labels,
                "positive_only_in_paper": len(only_paper),
                "positive_only_here": sum(a == 0 and b == 1 for a, b in zip(paper, labels)),
                # paper-only positives must all be clock-stamped write-tool outputs (timestamp artefacts)
                "paper_only_are_write_tools": all(rows[i]["function"] in WRITE_TOOLS for i in only_paper)}
        out["sets"][name] = entry
    return out


def _agentdojo_version():
    try:
        res = subprocess.run([str(AGENTDOJO_PY), "-c", "import importlib.metadata as m; print(m.version('agentdojo'))"],
                             capture_output=True, text=True, check=True)
        return res.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def assert_eval_only(row_ids, training_ids):
    """G3 guard: no agent-benchmark row may reach probe training or threshold choice."""
    overlap = set(row_ids) & set(training_ids)
    if overlap:
        raise AssertionError(f"{len(overlap)} agent-benchmark rows in training/threshold data")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--check", action="store_true", help="rebuild again in a temp folder and compare hashes")
    args = p.parse_args(argv)
    if args.check:
        recorded = json.loads(OUT.read_text(encoding="utf-8"))["sets"]
        with tempfile.TemporaryDirectory() as tmp:
            rebuild(Path(tmp))
            again = {name: sha256(Path(tmp) / fname) for name, fname, _ in SETS}
        diff = {n: (recorded[n]["sha256"][:12], h[:12]) for n, h in again.items() if recorded[n]["sha256"] != h}
        print("deterministic: same hashes" if not diff else f"hashes differ: {diff}")
        sys.exit(1 if diff else 0)
    rebuild(WORK)
    s = summarize(WORK)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(s, indent=2), encoding="utf-8")
    for name, e in s["sets"].items():
        print(name, e["rows"], "injected", e["injected"], "benign", e["benign"], e["sha256"][:12], e.get("vs_paper", ""))


if __name__ == "__main__":
    main()
