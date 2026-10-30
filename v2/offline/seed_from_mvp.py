"""Reuse the MVP's Qwen2.5-0.5B feature cache (same model, fp32, CPU, same rows) instead of ~1 h of re-extraction.

Copies mvp/offline/features/cache.npz → features/qwen0.5b/cache.npz and writes its run_meta with a "source" note.
tests/test_pipeline.py re-extracts a sample of rows with v2's extract.py and checks they match the copied cache.
"""
import json
import shutil

from common import FEATURES_ROOT, ROOT, Run, run_meta

MVP_CACHE = ROOT.parents[1] / "mvp" / "offline" / "features" / "cache.npz"


def main():
    run = Run("qwen0.5b", "fp32")
    run.features.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(MVP_CACHE, run.features / "cache.npz")
    meta = {**run_meta(run, "cpu"), "source": "mvp/offline/features/cache.npz (MVP extract.py, same model and rows)"}
    (run.features / "meta.json").write_text(json.dumps(meta, indent=2))
    print(f"seeded {FEATURES_ROOT / run.model} from the MVP cache")


if __name__ == "__main__":
    main()
