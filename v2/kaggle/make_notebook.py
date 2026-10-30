"""Writes anchor_3b.ipynb (Kaggle: Llama-3.2-3B runs of run_gpu.md). Edit the cells here, then rerun:
python kaggle/make_notebook.py   (tests/test_kaggle.py checks the notebook is current and its steps exist)
"""
import json
from pathlib import Path

NOTEBOOK = Path(__file__).with_name("anchor_3b.ipynb")


def md(s):
    return {"cell_type": "markdown", "metadata": {}, "source": s.strip("\n").splitlines(True)}


def code(s):
    return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [],
            "source": s.strip("\n").splitlines(True)}


CELLS = [
    md("""
# Anchor — Llama-3.2-3B runs on Kaggle (G1 smoke, G2 probe, G4 actions)

Runs the steps of `v2/offline/run_gpu.md` with `--model llama3b --precision nf4`: 4-bit NF4 weights, **bf16
compute**, the G1 build on Garv's RTX 2050, so one probe serves both machines. The T4 has no native bf16: step 1
checks that bf16 works and is fast enough here, and stops otherwise (then Garv's laptop runs every 3B step).

**Before Run all**
1. *Settings → Accelerator → GPU T4 x2* (one GPU is used). *Settings → Internet → On*.
2. *Add-ons → Secrets*: add `HF_TOKEN` (an account that accepted the Llama-3.2 licence) and attach it to this
   notebook. It is read into the environment only, never written to a file.
3. The code comes from `git clone` of the public repo, so `v2/` must be on GitHub first. Change `BRANCH` if needed.

**Output:** `/kaggle/working/anchor_llama3b_results.zip` with `out/llama3b/`, `data/llama3b/` and
`out/gpu_check_kaggle.json`. Download, unzip into `v2/offline/`, run the tests, commit. Features
(`features/llama3b/`, ~140 MB) stay in `/kaggle/working/anchor/…`; *Save Version* keeps them for a resume (last cell).

**Time:** first model download ~6.5 GB. Extract ≈ rows × 2 passes × the smoke pass time printed in step 4.
"""),
    code("""
# 0. Settings
REPO = "https://github.com/haragam22/anchor.git"
BRANCH = "main"
MODEL, PRECISION = "llama3b", "nf4"
RUN_EXTERNAL = True      # InjecAgent check (~400 rows x 2 passes)
RUN_ACTIONS = True       # 9 generations (G4 model actions) + demo scenarios
"""),
    code("""
# 1. GPU present?
import json, os, subprocess, sys, time
print(subprocess.run(["nvidia-smi"], capture_output=True, text=True).stdout)
import torch
assert torch.cuda.is_available(), "No GPU: Settings -> Accelerator -> GPU T4 x2"
print(torch.__version__, torch.cuda.get_device_name(0))
# The 3B build computes in bf16 (G1). Check it runs here and is not emulated-slow before spending GPU hours.
assert torch.cuda.is_bf16_supported(), "this GPU has no bf16: run the 3B steps on Garv's laptop instead"
a = torch.randn(512, 3072, device="cuda")
b = torch.randn(3072, 3072, device="cuda")
ms = {}
for dt in (torch.float16, torch.bfloat16):
    x, y = a.to(dt), b.to(dt)
    torch.mm(x, y); torch.cuda.synchronize(); t = time.perf_counter()
    for _ in range(20):
        torch.mm(x, y)
    torch.cuda.synchronize(); ms[str(dt)] = (time.perf_counter() - t) / 20 * 1000
print("ms per 512x3072x3072 matmul:", {k: round(v, 3) for k, v in ms.items()})
BF16_SLOWDOWN_LIMIT = 4.0  # bf16 vs fp16 on this GPU; above this, extraction would take many hours
assert ms["torch.bfloat16"] <= BF16_SLOWDOWN_LIMIT * ms["torch.float16"], "bf16 is emulated and too slow on this GPU"
"""),
    code("""
# 2. Code + pinned libraries (torch stays Kaggle's CUDA build)
WORK = "/kaggle/working"
ROOT = f"{WORK}/anchor"
if not os.path.isdir(ROOT):
    subprocess.run(["git", "clone", "--depth", "1", "--branch", BRANCH, REPO, ROOT], check=True)
else:
    subprocess.run(["git", "-C", ROOT, "pull", "--ff-only"], check=True)
OFFLINE = f"{ROOT}/v2/offline"
assert os.path.exists(f"{OFFLINE}/run_gpu.md"), "v2/ is not on GitHub yet"
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "transformers==5.21.0", "datasets==5.1.0",
                "scikit-learn==1.9.1", "bitsandbytes==0.50.2", "accelerate==1.15.0"], check=True)  # G1 pins
print(subprocess.run(["git", "-C", ROOT, "log", "-1", "--oneline"], capture_output=True, text=True).stdout)
"""),
    code("""
# 3. HF token from Kaggle Secrets -> environment only (/kaggle/working is saved as notebook output)
from kaggle_secrets import UserSecretsClient
os.environ["HF_TOKEN"] = UserSecretsClient().get_secret("HF_TOKEN")
os.environ["TOKENIZERS_PARALLELISM"] = "false"
assert os.environ["HF_TOKEN"].startswith("hf_"), "HF_TOKEN secret missing or wrong"
print("token loaded (not printed)")


def step(*args):
    \"\"\"Run one v2/offline script, stream its output, stop the notebook if it fails.\"\"\"
    print(">>>", " ".join(args), flush=True)
    t = time.time()
    p = subprocess.Popen([sys.executable, "-u", *args], cwd=OFFLINE, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True)
    for line in p.stdout:
        if "Loading weights" not in line:
            print(line, end="")
    assert p.wait() == 0, f"failed: {' '.join(args)}"
    print(f"--- {time.time() - t:.0f}s", flush=True)


M = ["--model", MODEL, "--precision", PRECISION]
"""),
    code("""
# 4. G1 on this GPU: capability check + 3B smoke (layer count, pass time)
step("check_gpu.py")
os.replace(f"{OFFLINE}/out/gpu_check.json", f"{OFFLINE}/out/gpu_check_kaggle.json")  # Garv's file keeps its name
step("smoke.py", *M)
smoke = json.load(open(f"{OFFLINE}/out/{MODEL}/smoke.json"))
print({k: smoke[k] for k in ("hidden_states", "tokens", "pass_s")})
"""),
    code("""
# 5. G2: dataset (Llama token budget) -> activations (resumable, checkpoint every 100 rows) -> probe
step("build_data.py", *M)
step("extract.py", *M)
step("train_probe.py", *M)
"""),
    code("""
# 6. External check (InjecAgent), model actions, the 9 demo scenarios
if RUN_EXTERNAL:
    step("external_eval.py", *M)
if RUN_ACTIONS:
    step("gen_actions.py", *M)
    if RUN_EXTERNAL:  # build_scenarios needs the external block in metrics.json
        step("build_scenarios.py", *M)
"""),
    code("""
# 7. Results at a glance
m = json.load(open(f"{OFFLINE}/out/{MODEL}/metrics.json"))
print("run_meta:", m["run_meta"]["model"], m["run_meta"]["precision"], m["run_meta"]["device"])
print("layer", m["layer"], "| threshold", m["threshold"], "|", m["verdict"])
print("shuffled-label AUROC", m["shuffled_label_control"]["test_auroc"])
for split in ("test", "heldout"):
    print(split, "AUROC", m["anchor"][split]["auroc"], "TPR", m["anchor"][split]["tpr"])
if "external" in m:
    print("InjecAgent", {k: m["external"]["anchor"][k] for k in ("auroc", "tpr", "false_block")})
if "hijacked" in m:
    print("hijacked", m["hijacked"])
"""),
    code("""
# 8. Zip what gets committed (never features/, .env or weights)
import pathlib, zipfile
off = pathlib.Path(OFFLINE)
dst = pathlib.Path(WORK) / "anchor_llama3b_results.zip"
files = [*(off / "out" / MODEL).rglob("*.json"), *(off / "data" / MODEL).rglob("*"), off / "out" / "gpu_check_kaggle.json"]
with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as z:
    for p in files:
        if p.is_file():
            assert p.name != ".env" and p.suffix not in (".npy", ".npz", ".safetensors"), p
            z.write(p, p.relative_to(off))
print(dst, round(dst.stat().st_size / 1e6, 2), "MB")
print("Download, unzip into v2/offline/, run the tests, then: git add v2/offline/out/llama3b v2/offline/data/llama3b")
"""),
    md("""
### Resume after a timeout
Kaggle stops a session after 12 h. Extract checkpoints every 100 rows into `features/llama3b/cache.npz`. To resume:
*Save Version* (keeps `/kaggle/working`), then in a new session add that version's output as input and copy its
`anchor/v2/offline/features/llama3b` folder into `OFFLINE/features/` before step 5. Rows already done are skipped.
"""),
]


def build():
    cells = [{**c, "id": f"cell-{i}"} for i, c in enumerate(CELLS)]
    return {"cells": cells, "nbformat": 4, "nbformat_minor": 5,
            "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                         "language_info": {"name": "python"},
                         "kaggle": {"accelerator": "nvidiaTeslaT4", "isInternetEnabled": True}}}


def render():
    return json.dumps(build(), indent=1, ensure_ascii=False) + "\n"


if __name__ == "__main__":
    NOTEBOOK.write_text(render(), encoding="utf-8")
    print(f"wrote {NOTEBOOK}")
