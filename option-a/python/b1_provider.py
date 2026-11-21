"""Loopback-only OpenAI-compatible provider for the B1 tool-call experiment."""

import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import re
import sys
import time
from uuid import uuid4

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
REVISION = "7ae557604adf67be50417f59c2c2f167def9a775"
TOOL_CALL = re.compile(r"<tool_call>\s*(.*?)\s*</tool_call>", re.DOTALL)


def generate(tokenizer, model, request, capture=False):
    messages = request["messages"]
    tools = request.get("tools", [])
    if not isinstance(messages, list) or not messages or not isinstance(tools, list):
        raise ValueError("Expected messages and optional tools arrays")
    for message in messages:
        if message["role"] not in {"system", "user", "assistant", "tool"}:
            raise ValueError("Unsupported message role")
        for call in message.get("tool_calls") or []:
            function = call["function"]
            if isinstance(function["arguments"], str):
                function["arguments"] = json.loads(function["arguments"])
    ids = tokenizer.apply_chat_template(
        messages, tools=tools, add_generation_prompt=True, tokenize=True, return_tensors="pt"
    )
    if not isinstance(ids, torch.Tensor):
        ids = ids["input_ids"]
    prompt_tokens = ids.shape[-1]
    if prompt_tokens > 8192:
        raise ValueError("B1 prompt exceeds 8192 tokens")
    with torch.inference_mode():
        output = model.generate(input_ids=ids, attention_mask=torch.ones_like(ids),
                                max_new_tokens=128, do_sample=False,
                                return_dict_in_generate=capture, output_hidden_states=capture)
    vector = None
    if capture:
        from b2_parity import prefill_vector

        vector = prefill_vector(tokenizer, model, ids, output)
        output = output.sequences
    generated = output[0, prompt_tokens:]
    raw = tokenizer.decode(generated, skip_special_tokens=True)
    calls = []
    for match in TOOL_CALL.finditer(raw):
        function = json.loads(match[1])
        if not isinstance(function["name"], str) or not isinstance(function["arguments"], dict):
            raise ValueError("Invalid model tool output")
        calls.append({"id": f"call_{uuid4().hex}", "type": "function", "function": {
            "name": function["name"], "arguments": json.dumps(function["arguments"]),
        }})
    if "<tool_call>" in TOOL_CALL.sub("", raw):
        raise ValueError("Incomplete model tool output")
    message = {"role": "assistant", "content": TOOL_CALL.sub("", raw).strip() or None}
    if calls:
        message["tool_calls"] = calls
    finish = "tool_calls" if calls else "length" if len(generated) == 128 else "stop"
    return message, finish, {"prompt_tokens": prompt_tokens, "completion_tokens": len(generated),
                             "total_tokens": prompt_tokens + len(generated)}, vector


class ProviderHandler(BaseHTTPRequestHandler):
    def begin_generation(self, request):
        return f"chatcmpl-{uuid4().hex}"

    def finish_generation(self, request_id, elapsed_ms):
        pass

    def audit(self, record):
        print(json.dumps(record), flush=True)

    def log_message(self, *_args):
        pass

    def respond(self, status, value):
        body = json.dumps(value).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/v1/models":
            self.respond(200, {"object": "list", "data": [{"id": MODEL, "object": "model"}]})
        else:
            self.respond(404, {"error": {"message": "Unknown route"}})

    def do_POST(self):
        if self.path != "/v1/chat/completions":
            self.respond(404, {"error": {"message": "Unknown route"}})
            return
        start = time.perf_counter()
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 262144:
                raise ValueError("Request length outside B1 limits")
            request = json.loads(self.rfile.read(length))
            if not isinstance(request, dict) or not isinstance(request.get("stream", False), bool):
                raise ValueError("Invalid chat request")
            options = request.get("stream_options")
            if options is not None and (not isinstance(options, dict)
                                        or not isinstance(options.get("include_usage", False), bool)):
                raise ValueError("Invalid stream options")
            if request["model"] != MODEL:
                raise ValueError("Requested model differs from the pinned model")
            roles = [message["role"] for message in request["messages"]]
            incoming = [message.get("tool_call_id") for message in request["messages"] if message["role"] == "tool"]
            request_id = self.begin_generation(request)
            self.audit({"event": "request", "roles": roles, "stream": request.get("stream", False),
                        "toolResultIds": incoming, "inferenceRequestId": self.headers.get("X-Anchor-Inference-Request-Id")})
            experiment = self.server.experiment
            message, finish, usage, vector = generate(self.server.tokenizer, self.server.model, request, experiment is not None)
        except (ValueError, KeyError, TypeError, AttributeError, RecursionError) as error:
            print(json.dumps({"event": "invalid", "type": type(error).__name__}), flush=True)
            self.respond(400, {"error": {"message": "Unsupported request or malformed model tool output"}})
            return
        self.finish_generation(request_id, (time.perf_counter()-start)*1000)
        if getattr(self.server,"profile_path",None) and roles == ["system","user","assistant","tool"]:
            # Private development capture. Only the digest and numeric results are published.
            self.server.profile_path.write_text(json.dumps({"messages":request["messages"],"tools":request["tools"]},
                                                         ensure_ascii=False),encoding="utf-8")
        self.audit({"event": "generated", "requestId": request_id, "finish": finish, "usage": usage,
                          "tools": [{"id": call["id"], "name": call["function"]["name"]}
                                    for call in message.get("tool_calls", [])],
                          "seconds": round(time.perf_counter() - start, 3)})
        result = None
        if experiment is not None:
            from b2_parity import historical_reference

            result = experiment.observe(request_id, request, vector,
                                        [call["id"] for call in message.get("tool_calls", [])],
                                        lambda messages: historical_reference(self.server.tokenizer, self.server.model, messages),
                                        self.isolate_prompt if self.server.isolate else None)
            print(json.dumps(result), flush=True)
        envelope = {"id": request_id, "created": int(time.time()), "model": MODEL}
        if request.get("stream"):
            self.stream(envelope, message, finish, usage, request)
        else:
            self.respond(200, {**envelope, "object": "chat.completion", "usage": usage,
                               "choices": [{"index": 0, "message": message, "finish_reason": finish}]})
        if (self.server.evaluate and result and result["outcome"] == "single_result_comparison"
                and not self.server.evaluation_started):
            from b2_evaluation import evaluate

            self.server.evaluation_started = True
            try:
                evidence = evaluate(self.server.tokenizer, self.server.model, experiment, request, request_id, self.server.split)
            except (ValueError, RuntimeError) as error:
                evidence = {"event": "b2_evaluation_error", "message": str(error)}
            print(json.dumps(evidence), flush=True)

    def isolate_prompt(self, request, historical, live):
        from b2_parity import isolate_prompt

        return isolate_prompt(self.server.tokenizer, self.server.model, self.server.experiment,
                              request, historical, live)

    def stream(self, envelope, message, finish, usage, request):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        for index, call in enumerate(message.get("tool_calls", [])):
            call["index"] = index
        base = {**envelope, "object": "chat.completion.chunk"}
        for delta, reason in ((message, None), ({}, finish)):
            chunk = {**base, "choices": [{"index": 0, "delta": delta, "finish_reason": reason}]}
            self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode())
        if (request.get("stream_options") or {}).get("include_usage"):
            self.wfile.write(f"data: {json.dumps({**base, 'choices': [], 'usage': usage})}\n\n".encode())
        self.wfile.write(b"data: [DONE]\n\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--capture-profile", type=Path)
    parser.add_argument("--parity", action="store_true", help="Collect controlled B2 diagnostics")
    parser.add_argument("--isolate-prompt", action="store_true", help="Compare prompt factors during B2")
    parser.add_argument("--evaluate", action="store_true", help="Evaluate the frozen probe on the MVP test split")
    parser.add_argument("--split", choices=["test","heldout"], default="test")
    args = parser.parse_args()
    if args.snapshot.name != REVISION:
        parser.error(f"Expected snapshot directory {REVISION}")
    torch.set_num_threads(max(1, (os.cpu_count() or 2) // 2))
    start = time.perf_counter()
    with HTTPServer(("127.0.0.1", args.port), ProviderHandler) as server:
        server.tokenizer = AutoTokenizer.from_pretrained(args.snapshot, local_files_only=True)
        server.model = AutoModelForCausalLM.from_pretrained(args.snapshot, dtype=torch.float32,
                                                              local_files_only=True).eval()
        server.experiment = None
        server.profile_path = args.capture_profile
        server.isolate = args.isolate_prompt
        server.evaluate = args.evaluate
        server.split = args.split
        server.evaluation_started = False
        if args.parity or args.isolate_prompt or args.evaluate:
            from b2_parity import ParityExperiment, ROOT, verify_saved_fixture

            sys.path.insert(0, str(ROOT / "mvp/offline"))
            server.experiment = ParityExperiment()
            print(json.dumps(verify_saved_fixture(server.tokenizer, server.model, server.experiment)), flush=True)
        print(json.dumps({"event": "ready", "port": server.server_port, "revision": REVISION,
                          "loadSeconds": round(time.perf_counter() - start, 3)}), flush=True)
        server.serve_forever()


if __name__ == "__main__":
    main()
