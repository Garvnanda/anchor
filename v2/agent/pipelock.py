"""Pipelock v3.7.1 (unmodified binary) as the agent's network layer: fetch proxy for reads, forward proxy for mail.

Config = the `balanced` preset with three changes, all config (no code change): the mock server's loopback address
is allowed past the SSRF guard (`ssrf.ip_allowlist`), the forward proxy is on, and the demo secret is registered
as a canary token, so body DLP blocks any request that carries it.
"""
import json
import os
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import yaml

BINARY = Path(os.environ.get("PIPELOCK", Path.home() / "tools" / "pipelock" / "pipelock.exe"))
VERSION = "v3.7.1"


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def config(secret, workdir):
    raw = Path(workdir) / "balanced.yaml"
    subprocess.run([str(BINARY), "generate", "config", "--preset", "balanced", "--output", str(raw)],
                   check=True, capture_output=True)
    cfg = yaml.safe_load(raw.read_text(encoding="utf-8"))
    cfg["ssrf"]["ip_allowlist"] = ["127.0.0.1/32"]
    cfg["forward_proxy"]["enabled"] = True
    cfg["canary_tokens"] = {"enabled": True, "tokens": [{"name": "demo_api_key", "value": secret}]}
    path = Path(workdir) / "pipelock.yaml"
    path.write_text(yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return path


class Pipelock:
    def __init__(self, secret):
        self.secret = secret
        self.dir = tempfile.mkdtemp(prefix="pipelock-")
        self.port = free_port()
        self.proc = None
        self.log_path = Path(self.dir) / "pipelock.log"

    @property
    def url(self):
        return f"http://127.0.0.1:{self.port}"

    def start(self, wait_s=15):
        cfg = config(self.secret, self.dir)
        self._log = open(self.log_path, "w", encoding="utf-8")
        self.proc = subprocess.Popen([str(BINARY), "run", "--config", str(cfg), "--listen", f"127.0.0.1:{self.port}"],
                                     stdout=self._log, stderr=subprocess.STDOUT)
        deadline = time.time() + wait_s
        while time.time() < deadline:
            try:
                urllib.request.urlopen(f"{self.url}/health", timeout=1)
                return self
            except (urllib.error.URLError, ConnectionError, OSError):
                if self.proc.poll() is not None:
                    break
                time.sleep(0.2)
        self.stop()
        raise RuntimeError("pipelock did not start")

    def fetch(self, target):
        """GET through the fetch proxy → (text or None, verdict dict)."""
        try:
            with urllib.request.urlopen(f"{self.url}/fetch?url={urllib.parse.quote(target, safe='')}", timeout=30) as r:
                v = json.loads(r.read().decode("utf-8"))
            return (None if v.get("blocked") else v.get("content", "")), {"layer": "pipelock", "blocked": bool(v.get("blocked")),
                                                                          "status": r.status, "reason": v.get("block_reason")}
        except urllib.error.HTTPError as e:
            return None, {"layer": "pipelock", "blocked": True, "status": e.code, "reason": e.read().decode("utf-8", "replace")[:300]}

    def post(self, target, payload):
        """POST JSON through the forward proxy → verdict dict (blocked + reason when DLP stops it)."""
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({"http": self.url}))
        req = urllib.request.Request(target, data=json.dumps(payload).encode("utf-8"), method="POST",
                                     headers={"content-type": "application/json"})
        try:
            with opener.open(req, timeout=30) as r:
                return {"layer": "pipelock", "blocked": False, "status": r.status}
        except urllib.error.HTTPError as e:
            return {"layer": "pipelock", "blocked": True, "status": e.code, "reason": e.read().decode("utf-8", "replace")[:300]}

    def stop(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        if getattr(self, "_log", None):
            self._log.close()

    def __enter__(self):
        return self.start()

    def __exit__(self, *exc):
        self.stop()
