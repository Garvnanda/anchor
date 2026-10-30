"""G1 gate: the committed GPU check and 3B smoke files show the 3B setup works on the RTX 2050 at the fixed precision.

Checks committed files only (no GPU or model needed), so it runs on either laptop.
"""
import json
import sys
from pathlib import Path

OFFLINE = Path(__file__).resolve().parents[1] / "offline"
OUT = OFFLINE / "out"
sys.path.insert(0, str(OFFLINE))


def load(name):
    return json.loads((OUT / name).read_text())


def test_gpu_check_supports_4bit_on_cuda():
    r = load("gpu_check.json")
    assert r["cuda_available"] is True
    assert r["bitsandbytes_4bit_ok"] is True
    assert isinstance(r["bf16_supported"], bool)


def test_smoke_precision_is_the_g1_decision():
    """NF4 weights; bf16 compute exactly when the GPU check says bf16 is supported, else fp16."""
    prec = load("smoke_llama3b.json")["run_meta"]["precision"]
    bf16 = load("gpu_check.json")["bf16_supported"]
    assert prec == {"weights": "nf4", "compute_dtype": "bfloat16" if bf16 else "float16", "double_quant": False}


def test_smoke_run_meta_complete():
    meta = load("smoke_llama3b.json")["run_meta"]
    assert meta["model"] == "meta-llama/Llama-3.2-3B-Instruct"
    assert {"precision", "device", "torch", "cuda", "transformers", "bitsandbytes", "date"} <= set(meta)
    assert "RTX 2050" in meta["device"]


def test_smoke_hidden_states_and_page_size():
    r = load("smoke_llama3b.json")
    assert r["num_layers"] == 28 and r["hidden_states"] == 29  # embeddings + 28 layers
    assert r["page_tokens"] >= 400
    assert r["hidden_state_finite"] is True


def test_smoke_vram_headroom_at_least_half_gb():
    r = load("smoke_llama3b.json")
    assert r["headroom_gb"] >= 0.5
    assert abs(r["vram_total_gb"] - r["peak_reserved_gb"] - r["headroom_gb"]) < 0.01


def test_smoke_rendered_prompt_checks_pass():
    r = load("smoke_llama3b.json")
    assert r["rendered_checks"] == {"page_in_tool_role": True, "fetch_call_rendered": True,
                                    "ends_at_assistant_start": True, "fixed_date": True}


def test_smoke_timing_recorded():
    r = load("smoke_llama3b.json")
    assert len(r["pass_s"]) >= 3 and all(t > 0 for t in r["pass_s"])
    assert abs(r["pass_s_mean"] - sum(r["pass_s"]) / len(r["pass_s"])) < 1e-3


def test_check_rendered_rejects_page_outside_tool_role():
    """The render check itself must fail when the page arrives as a user message or the prompt doesn't end at
    assistant start (guards the check, not just its committed output)."""
    smoke = __import__("smoke_llama3b")
    page = "The library reopened in May."
    good = ("<|start_header_id|>user<|end_header_id|>\n\ntask<|eot_id|>"
            '<|start_header_id|>assistant<|end_header_id|>\n\n{"name": "fetch_page", "parameters": {}}<|eot_id|>'
            f"<|start_header_id|>ipython<|end_header_id|>\n\n{page}<|eot_id|>"
            "<|start_header_id|>assistant<|end_header_id|>\n\n")
    good = f"Today Date: {smoke.DATE_STRING}\n" + good
    assert all(smoke.check_rendered(good, page).values())
    as_user = good.replace("ipython", "user")
    assert smoke.check_rendered(as_user, page)["page_in_tool_role"] is False
    assert smoke.check_rendered(good.rstrip(), page)["ends_at_assistant_start"] is False


def test_run_gpu_md_has_g2_estimate_from_smoke():
    text = (OFFLINE / "run_gpu.md").read_text(encoding="utf-8")
    assert "G2" in text and "smoke_llama3b.json" in text
    assert f"{load('smoke_llama3b.json')['pass_s_mean']}" in text
