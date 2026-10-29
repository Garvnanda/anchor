"""Phase 0: what can this machine run? Checks CUDA, bf16/fp16 support and speed, free VRAM and the 4-bit path.

Run on the GPU laptop:  python check_gpu.py            (writes out/gpu_check.json)
Needs only torch (CUDA build); bitsandbytes is optional and only tested if installed.
"""
import json
import platform
import time
from pathlib import Path

import torch

OUT = Path(__file__).parent / "out" / "gpu_check.json"


def timed_mm(dtype, device, n=10):
    a = torch.randn(512, 3072, device=device, dtype=dtype)
    b = torch.randn(3072, 3072, device=device, dtype=dtype)
    torch.mm(a, b)
    if device == "cuda":
        torch.cuda.synchronize()
    t = time.perf_counter()
    for _ in range(n):
        torch.mm(a, b)
    if device == "cuda":
        torch.cuda.synchronize()
    return round((time.perf_counter() - t) / n * 1000, 3)


def main():
    r = {"os": platform.platform(), "python": platform.python_version(), "torch": torch.__version__,
         "cuda_available": torch.cuda.is_available(), "cuda_version": torch.version.cuda}
    if r["cuda_available"]:
        props = torch.cuda.get_device_properties(0)
        free, total = torch.cuda.mem_get_info()
        r |= {"gpu": props.name, "compute_capability": f"{props.major}.{props.minor}",
              "vram_total_gb": round(total / 1e9, 2), "vram_free_gb": round(free / 1e9, 2),
              "bf16_supported": torch.cuda.is_bf16_supported(),
              "ms_per_matmul": {str(dt): timed_mm(dt, "cuda") for dt in (torch.float32, torch.float16, torch.bfloat16)}}
        # Llama-3.2-3B weights: ~3.2e9 params. bf16/fp16 = 2 bytes, 4-bit ≈ 0.55 bytes incl. overhead.
        r["llama3b_weights_gb_estimate"] = {"bf16": 6.4, "fp16": 6.4, "4bit": 1.8}
        r["llama3b_bf16_fits"] = r["vram_free_gb"] > 6.4 + 0.8
        try:
            import bitsandbytes as bnb  # noqa: F401

            r["bitsandbytes"] = bnb.__version__
            lin = bnb.nn.Linear4bit(3072, 3072, compute_dtype=torch.bfloat16 if r["bf16_supported"] else torch.float16,
                                    quant_type="nf4").cuda()
            x = torch.randn(512, 3072, device="cuda", dtype=lin.compute_dtype)
            lin(x)
            r["bitsandbytes_4bit_ok"] = True
        except Exception as e:  # report, don't crash: this is a capability check
            r["bitsandbytes"] = r.get("bitsandbytes", "not installed")
            r["bitsandbytes_4bit_ok"] = f"no: {type(e).__name__}: {e}"[:200]
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(r, indent=2))
    print(json.dumps(r, indent=2))


if __name__ == "__main__":
    main()
