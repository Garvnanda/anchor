"""check_gpu.py runs and reports without CUDA (the dev laptop) and never crashes on missing bitsandbytes."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "offline"))
import check_gpu  # noqa: E402


def test_runs_without_cuda_and_writes_report(tmp_path, monkeypatch):
    out = tmp_path / "gpu_check.json"
    monkeypatch.setattr(check_gpu, "OUT", out)
    check_gpu.main()
    r = json.loads(out.read_text())
    assert {"os", "torch", "cuda_available"} <= set(r)
    if not r["cuda_available"]:
        assert "bf16_supported" not in r  # GPU fields only when a GPU is present
