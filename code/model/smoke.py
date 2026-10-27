"""
Smoke test — one live model call + VRAM / latency print.
Run: python code/model/smoke.py
"""

import os
import sys
import time

from dotenv import load_dotenv
load_dotenv()


def main():
    hf_token = os.getenv("HF_TOKEN")
    if not hf_token or hf_token.startswith("hf_YOUR"):
        print("⚠  No valid HF_TOKEN. Set it in .env to run a live smoke test.")
        print("   Mock mode will still work for the demo.")
        sys.exit(0)

    try:
        import torch
        from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

        model_id = "meta-llama/Llama-3.2-3B-Instruct"
        print(f"Loading {model_id} (4-bit)…")

        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
        )

        tokenizer = AutoTokenizer.from_pretrained(model_id, token=hf_token)
        model = AutoModelForCausalLM.from_pretrained(
            model_id,
            quantization_config=bnb_config,
            device_map="auto",
            token=hf_token,
        )
        model.eval()

        vram = torch.cuda.memory_allocated() / 1024**2
        print(f"✓ Model loaded. VRAM: {vram:.0f} MB")

        # One generation with hidden states
        prompt = "What is the capital of France?"
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

        t0 = time.perf_counter()
        with torch.no_grad():
            out = model.generate(
                **inputs,
                max_new_tokens=32,
                output_hidden_states=True,
                return_dict_in_generate=True,
            )
        elapsed = time.perf_counter() - t0

        text = tokenizer.decode(out.sequences[0], skip_special_tokens=True)
        print(f"✓ Generation ({elapsed:.2f}s): {text}")
        print(f"  Hidden state layers: {len(out.hidden_states[0])}")
        print(f"  Hidden dim: {out.hidden_states[0][0].shape[-1]}")
        print(f"  VRAM after generation: {torch.cuda.memory_allocated() / 1024**2:.0f} MB")

    except Exception as e:
        print(f"✗ Smoke test failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
