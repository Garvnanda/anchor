"""Check: load the model, one chat-template forward pass, print layers, timing and the rendered prompt."""
import json
import time

import torch

from common import load_model, messages, parse, prompt_ids, render, run_meta

TASK = "Summarize this page and email me the notes."
PAGE = "The library reopened in May after a two-year renovation of the main hall."


def main(argv=None):
    run, _ = parse(argv, __doc__)
    t0 = time.time()
    tok, model, device = load_model(run)
    load_s = time.time() - t0

    rendered = render(tok, messages(TASK, PAGE))
    ids = prompt_ids(tok, TASK, PAGE, device=device)
    with torch.no_grad():
        model(ids, output_hidden_states=True)  # warm-up
        t1 = time.time()
        hs = model(ids, output_hidden_states=True).hidden_states
        pass_s = time.time() - t1

    print(rendered)
    print(f"hidden_states={len(hs)} tokens={ids.shape[1]} load={load_s:.1f}s pass={pass_s:.3f}s")
    assert len(hs) == run.spec["n_layers"] + 1, len(hs)
    assert PAGE in rendered.split(TASK)[-1]  # page comes after the task, in the tool turn
    if run.model == "qwen0.5b":
        assert "<tool_response>" in rendered and rendered.rstrip().endswith("<|im_start|>assistant")
    else:
        assert "ipython<|end_header_id|>" in rendered and rendered.rstrip().endswith("assistant<|end_header_id|>")

    run.out.mkdir(parents=True, exist_ok=True)
    (run.out / "smoke.json").write_text(json.dumps(
        {"run_meta": run_meta(run, device), "hidden_states": len(hs), "tokens": int(ids.shape[1]), "load_s": round(load_s, 1),
         "pass_s": round(pass_s, 3), "torch": torch.__version__}, indent=2))


if __name__ == "__main__":
    main()
