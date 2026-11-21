"""Authenticated loopback startup for the pinned provider with B2 incompatibility exposed."""
import argparse
import hashlib
import hmac
import json
import os
import re
from collections import OrderedDict
from pathlib import Path
from http.server import ThreadingHTTPServer
from threading import Lock
from urllib.parse import urlsplit, parse_qs

from b1_provider import ProviderHandler, REVISION

ASSETS = {
    "config.json": "18e18afcaccafade98daf13a54092927904649e1dd4eba8299ab717d5d94ff45",
    "generation_config.json": "e558847a8b4402616f1273797b015104dc266fe4b520056fca88823ba8f8ebe6",
    "model.safetensors": "fdf756fa7fcbe7404d5c60e26bff1a0c8b8aa1f72ced49e7dd0210fe288fb7fe",
    "tokenizer_config.json": "5b5d4f65d0acd3b2d56a35b56d374a36cbc1c8fa5cf3b3febbbfabf22f359583",
    "tokenizer.json": "c0382117ea329cdf097041132f6d735924b697924d6f6fc3945713e96ce87539",
    "vocab.json": "ca10d7e9fb3ed18575dd1e277a2579c16d108e32f27439684afa0e10b1440910",
    "merges.txt": "599bab54075088774b1733fde865d5bd747cbcc7a547c5bc12610e874e26f5e3",
}

class ManagedHandler(ProviderHandler):
    timeout = 30

    def audit(self, record):
        # Request and tool identifiers may contain caller-controlled content.
        safe = {"event": record["event"]}
        if record["event"] == "generated":
            safe.update(usage=record["usage"], seconds=record["seconds"])
        print(json.dumps(safe), flush=True)

    def begin_generation(self, request):
        if getattr(self.server, "showcase_metrics", False):
            contents = [m.get("content") for m in request["messages"] if m.get("role") == "tool"]
            print(json.dumps({"event":"tool_context","count":len(contents),
                  "marked":any("[Anchor: untrusted tool result]" in json.dumps(value) for value in contents)}),flush=True)
        self.correlated = None
        fields = [self.headers.get_all("X-Anchor-" + name, []) for name in
                  ("Inference-Request-Id", "Run-Id", "Session-Id")]
        if not any(fields):
            return super().begin_generation(request)
        identifier = r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}"
        if any(len(values) != 1 or not re.fullmatch(identifier, values[0]) for values in fields):
            raise ValueError("Incomplete correlation")
        inference, run, session = (values[0] for values in fields)
        records = self.server.records
        if inference in records:
            raise ValueError("Duplicate inference request")
        pending = set()
        observed = set()
        for message in request["messages"]:
            role = message["role"]
            if role == "assistant":
                pending.clear()
                observed.clear()
                for call in message.get("tool_calls") or []:
                    key = call["id"]
                    if not re.fullmatch(identifier, key) or key in pending:
                        raise ValueError("Ambiguous tool call")
                    pending.add(key)
            elif role == "tool":
                key = message.get("tool_call_id")
                if key not in pending:
                    raise ValueError("Unmatched tool result")
                pending.remove(key)
                observed.add(key)
            else:
                pending.clear()
                observed.clear()
        if len(records) >= 512:
            records.popitem(last=False)
        records[inference] = {}
        self.correlated = (run, session, observed)
        return inference

    def finish_generation(self, request_id, elapsed_ms):
        if self.correlated is None:
            return
        run, session, tools = self.correlated
        for tool in tools:
            self.server.records[request_id][tool] = {
                "schemaVersion": 1, "status": "incompatible", "detectorMode": "direct_managed_qwen",
                "runId": run, "sessionId": session, "inferenceRequestId": request_id, "toolCallId": tool,
                "provenance": None, "score": None, "threshold": None, "latencyMs": elapsed_ms,
                "errorCode": "PROBE_CONTEXT_INCOMPATIBLE",
            }

    def authorized(self):
        host = self.headers.get("Host", "")
        if host != f"127.0.0.1:{self.server.server_port}" or self.headers.get("Origin"):
            self.respond(403, {"errorCode": "UNTRUSTED_ORIGIN"})
            return False
        expected = "Bearer " + self.server.token
        if not hmac.compare_digest(self.headers.get("Authorization", "").encode(), expected.encode()):
            self.respond(401, {"errorCode": "UNAUTHORIZED"})
            return False
        return True

    def do_GET(self):
        if not self.authorized():
            return
        path = urlsplit(self.path).path
        if path == "/health":
            self.respond(200, {"schemaVersion": 1, "status": "incompatible"})
        elif path == "/metadata":
            self.respond(200, {"schemaVersion": 1, "provenance": None, "toolCalling": True, "streaming": True})
        elif path.startswith("/v1/activations/"):
            keys = parse_qs(urlsplit(self.path).query).get("toolCallId", [])
            records = self.server.records.get(path.removeprefix("/v1/activations/"), {})
            if len(keys) == 1 and keys[0] in records:
                self.respond(200, records[keys[0]])
            else:
                self.respond(404, {"errorCode": "NO_COMPATIBLE_ACTIVATION"})
        else:
            super().do_GET()

    def do_POST(self):
        if not self.authorized():
            return
        if not self.server.inference_lock.acquire(blocking=False):
            self.respond(503, {"errorCode": "PROVIDER_BUSY"})
            return
        try:
            limit = getattr(self.server, "showcase_limit", 0)
            if limit and self.server.showcase_requests >= limit:
                print(json.dumps({"event":"showcase_budget_reached"}),flush=True)
                self.respond(400, {"error":{"message":"Controlled showcase turn budget reached"}})
                return
            if limit:
                self.server.showcase_requests += 1
            super().do_POST()
        except (BrokenPipeError, ConnectionResetError, TimeoutError):
            self.close_connection = True
        finally:
            self.server.inference_lock.release()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, default=Path.home()/".cache/huggingface/hub/models--Qwen--Qwen2.5-0.5B-Instruct/snapshots"/REVISION)
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--probe", type=Path, default=Path(__file__).resolve().parents[2]/"v2/offline/out/qwen0.5b/probe.json")
    parser.add_argument("--showcase-metrics",action="store_true")
    parser.add_argument("--showcase-turn-limit",type=int,choices=range(1,9))
    args = parser.parse_args()
    token = os.environ.get("ANCHOR_DETECTOR_TOKEN")
    if not token:
        parser.error("Set ANCHOR_DETECTOR_TOKEN before starting the service")
    if not args.probe.is_file():
        parser.error(f"Missing probe artifact {args.probe}")
    if hashlib.sha256(args.probe.read_bytes()).hexdigest() != "6654792a7a27ee9ea700578842d6a8b3668313bdcef91e55473fe5afe8fd938a":
        parser.error("Incompatible probe artifact")
    for name, digest in ASSETS.items():
        path = args.snapshot/name
        if not path.is_file():
            parser.error(f"Missing snapshot asset {path}")
        with path.open("rb") as handle:
            if hashlib.file_digest(handle, "sha256").hexdigest() != digest:
                parser.error(f"Incompatible snapshot asset {name}")
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM
    torch.set_num_threads(max(1,(os.cpu_count() or 2)//2))
    with ThreadingHTTPServer(("127.0.0.1",args.port),ManagedHandler) as server:
        server.token = token
        server.inference_lock = Lock()
        server.records = OrderedDict()
        server.experiment = None
        server.showcase_limit = args.showcase_turn_limit
        server.showcase_requests = 0
        server.showcase_metrics = args.showcase_metrics
        server.evaluate = False
        server.tokenizer = AutoTokenizer.from_pretrained(args.snapshot,local_files_only=True)
        server.model = AutoModelForCausalLM.from_pretrained(args.snapshot,dtype=torch.float32,local_files_only=True).eval()
        print(json.dumps({"port":server.server_port,"detectorStatus":"incompatible"}),flush=True)
        server.serve_forever()

if __name__=="__main__":
    main()
