"""Kaggle notebook (3B runs): current with its generator, valid cells, every step exists and takes the switch."""
import ast
import json
import re
import sys
from pathlib import Path

V2 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(V2 / "kaggle"))
sys.path.insert(0, str(V2 / "offline"))

import make_notebook  # noqa: E402
from common import parse  # noqa: E402

NB = json.loads(make_notebook.NOTEBOOK.read_text(encoding="utf-8"))
CODE = ["".join(c["source"]) for c in NB["cells"] if c["cell_type"] == "code"]
ALL = "\n".join(CODE)


def test_notebook_is_current_with_its_generator():
    assert make_notebook.NOTEBOOK.read_text(encoding="utf-8") == make_notebook.render()


def test_every_code_cell_parses():
    for src in CODE:
        ast.parse(src)


def test_every_step_script_exists_and_takes_the_3b_switch():
    steps = re.findall(r'step\("([a-z_]+\.py)"', ALL)
    assert steps[:2] == ["check_gpu.py", "smoke.py"] and "extract.py" in steps and "train_probe.py" in steps
    for s in steps:
        assert (V2 / "offline" / s).exists(), s
    run, _ = parse(["--model", "llama3b", "--precision", "nf4"])
    assert (run.model, run.precision) == ("llama3b", "nf4")
    assert 'MODEL, PRECISION = "llama3b", "nf4"' in ALL


def test_steps_follow_run_gpu_order():
    steps = re.findall(r'step\("([a-z_]+\.py)"', ALL)
    order = ["build_data.py", "extract.py", "train_probe.py", "external_eval.py", "gen_actions.py", "build_scenarios.py"]
    assert [s for s in steps if s in order] == order


def test_token_never_written_or_printed():
    assert 'UserSecretsClient().get_secret("HF_TOKEN")' in ALL
    for src in CODE:
        assert not re.search(r"open\([^)]*\.env", src) and "write_text(os.environ" not in src
        assert not re.search(r"print\([^)]*HF_TOKEN", src)


def test_zip_excludes_features_and_weights():
    zip_cell = next(s for s in CODE if "zipfile" in s)
    assert "features" not in zip_cell.split("files =")[1].split("\n")[0]
    assert '".npy", ".npz", ".safetensors"' in zip_cell
