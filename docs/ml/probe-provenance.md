# B0 probe provenance

| Item | Evidence |
| --- | --- |
| Model | Historical source loads `Qwen/Qwen2.5-0.5B-Instruct` without a revision. Local snapshot `7ae557604adf67be50417f59c2c2f167def9a775` is available. Historical metadata does not bind training to that snapshot. |
| Cached weights | `model.safetensors` SHA-256 `fdf756fa7fcbe7404d5c60e26bff1a0c8b8aa1f72ced49e7dd0210fe288fb7fe`. |
| Cached tokenizer and template | `tokenizer.json` SHA-256 `c0382117ea329cdf097041132f6d735924b697924d6f6fc3945713e96ce87539`. `tokenizer_config.json` SHA-256 `5b5d4f65d0ac3b2d56a35b56d374a36cbc1c8fa5cf3b3febbbfabf22f359583`. The historical hash is unrecorded. |
| Feature definition | MVP renders the system and user messages with the native template and `add_generation_prompt=True`. The full context appends an assistant `fetch_page` call and a native tool result. Subtract the task-only vector from the full-context vector at `hidden_states[9][0, -1]`, the final token of each rendered prompt. The vector has 896 components. |
| Probe | `v2/offline/out/qwen0.5b/probe.json` SHA-256 `6654792a7a27ee9ea700578842d6a8b3668313bdcef91e55473fe5afe8fd938a`. Layer, threshold, scaler mean/scale, coefficients and intercept match `mvp/offline/out/probe.json`. Position is inferred from the MVP extractor. Standardize the delta, apply the logistic regression and compare the probability with `0.43131598830223083`. |
| Precision | CPU FP32 recorded. Probe metadata lists Python 3.12.10, torch 2.14.1+cpu, Transformers 5.21.0, NumPy 2.5.4 and scikit-learn 1.9.1. The copied v2 feature metadata lists Python 3.12.14. |
| Dataset | MVP split counts match probe metadata (971 train, 214 validation, 205 test, 44 held out). MVP rows SHA-256 `865230c1079644eb3a1bccdf0b6702b4b75cadee7f646cd0a8682bf09eedaf5`. The tracked v2 rows have 1,917 train, 420 validation, 405 test and 130 held out. |
| Feature cache | MVP and v2 Qwen layer-9 arrays share SHA-256 `4c12f208cc4564aeb38324df38087713053b2ecd8a04010b38aa8f56bcd266b4`. Their `ids.json` hashes match. The v2 cache metadata identifies the MVP cache as its source. |

## Local reproduction

With the owner's approval, loaded the cached snapshot offline in CPU FP32 using the existing Python 3.12.14 environment with torch 2.14.1+cu130. Verified the saved feature IDs match the MVP dataset row order and that the feature array is 1,434 × 896. Used the original MVP prompt builder to recompute layer-9 deltas for the first, middle and last row of each train, validation, test and held-out split. All 896 values in each of the 12 vectors matched the saved values exactly. The maximum absolute difference was zero for both the features and probe scores, and all 12 threshold decisions matched.

This establishes that the approved local snapshot reproduces the saved features on the checked rows. The original training revision remains unrecorded. This check used MVP prompts. Parity for actual OpenCode requests remains a B2 gate.

The tracked metrics are historical offline results. Test AUROC was 0.9979 with 127/132 positives detected. The InjecAgent check reported 20/200 detected and 0/102 benign false blocks. These evaluations were not rerun during B0.

`v2/offline/common.py` and `v2/offline/extract.py` contain tracked merge-conflict markers. The historical `v2/anchor/scorer.py` reconstructs prompts in separate forwards. Option A requires evidence from the actual generation path, including a traceable task-only baseline.
