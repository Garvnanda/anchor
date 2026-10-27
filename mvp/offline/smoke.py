"""Phase 1 check: load the model, one chat-template forward pass, print layers, timing and the rendered prompt."""
import json
import time

import torch

from common import OUT, load_model, messages, prompt_ids

TASK = "Summarize this page and email me the notes."
PAGE = "The library reopened in May after a two-year renovation of the main hall."


def main():
    t0 = time.time()
    tok, model = load_model()
    load_s = time.time() - t0

    rendered = tok.apply_chat_template(messages(TASK, PAGE), add_generation_prompt=True, tokenize=False)
    ids = prompt_ids(tok, TASK, PAGE)
    with torch.no_grad():
        model(ids, output_hidden_states=True)  # warm-up
        t1 = time.time()
        hs = model(ids, output_hidden_states=True).hidden_states
        pass_s = time.time() - t1

    print(rendered)
    print(f"hidden_states={len(hs)} tokens={ids.shape[1]} load={load_s:.1f}s pass={pass_s:.3f}s")
    assert len(hs) == 25, len(hs)
    assert "<tool_response>" in rendered and PAGE in rendered.split("<tool_response>")[1]
    assert rendered.rstrip().endswith("<|im_start|>assistant")

    OUT.mkdir(exist_ok=True)
    (OUT / "smoke.json").write_text(json.dumps(
        {"hidden_states": len(hs), "tokens": int(ids.shape[1]), "load_s": round(load_s, 1),
         "pass_s": round(pass_s, 3), "torch": torch.__version__}, indent=2))


if __name__ == "__main__":
    main()
