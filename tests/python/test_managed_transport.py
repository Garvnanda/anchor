"""Exercise the real managed Qwen process from an independent HTTP client."""
import json
import os
from pathlib import Path
import secrets
import subprocess
import socket
import time
import unittest
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]


class ManagedTransportTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.token = secrets.token_urlsafe(32)
        cls.start()
        cls.addClassCleanup(cls.stop)

    @classmethod
    def start(cls):
        python = os.environ.get("ANCHOR_PYTHON", ROOT / "option-a/.cache/b7-verify/Scripts/python.exe")
        cls.process = subprocess.Popen([python, "-B", ROOT / "option-a/python/serve.py"],
                                       env={**os.environ, "ANCHOR_DETECTOR_TOKEN": cls.token},
                                       stdout=subprocess.PIPE, text=True)
        ready = json.loads(cls.process.stdout.readline())
        cls.url = f"http://127.0.0.1:{ready['port']}"

    @classmethod
    def stop(cls):
        cls.process.terminate()
        cls.process.wait(timeout=30)
        cls.process.stdout.close()

    def http(self, path, body=None, headers=None):
        options = {"Authorization": "Bearer " + self.token, "Content-Type": "application/json", **(headers or {})}
        request = Request(self.url + path, data=json.dumps(body).encode() if body is not None else None,
                          headers=options)
        try:
            response = urlopen(request, timeout=60)
        except HTTPError as error:
            response = error
        with response:
            return response.status, json.load(response)

    def test_correlated_failure_and_process_loss(self):
        chat = "/v1/chat/completions"
        result = "/v1/activations/request1?toolCallId="
        headers = {"X-Anchor-Inference-Request-Id":"request1","X-Anchor-Run-Id":"run1",
                   "X-Anchor-Session-Id":"session1"}
        calls = [{"id": key,"type":"function","function":{"name":"get_color","arguments":"{}"}}
                 for key in ("call1","call2")]
        messages = [{"role":"user","content":"Reply with the two returned colors."},
                    {"role":"assistant","content":"","tool_calls":calls},
                    {"role":"tool","tool_call_id":"call1","content":"blue"},
                    {"role":"tool","tool_call_id":"call2","content":"green"}]
        body = {"model":"Qwen/Qwen2.5-0.5B-Instruct","messages":messages}
        for bad_fields in ({"stream":"yes"},{"stream_options":["invalid"]},{"stream_options":{"include_usage":1}}):
            self.assertEqual(self.http(chat,{**body,**bad_fields},headers)[0],400)
        self.assertEqual(self.http(chat,body,{"X-Anchor-Run-Id":"partial"})[0],400)
        self.assertEqual(self.http(chat,{**body,"messages":messages+[messages[-1]]},headers)[0],400)
        status, completion = self.http(chat,body,headers)
        self.assertEqual(status,200)
        self.assertEqual(completion["id"],"request1")
        validator = Draft202012Validator(json.loads((ROOT/"contracts/detector-result.schema.json").read_text()))
        for key in ("call1","call2"):
            status, record = self.http(result+key)
            self.assertEqual(status,200)
            validator.validate(record)
            self.assertEqual([record[k] for k in ("runId","sessionId","inferenceRequestId","toolCallId")],
                             ["run1","session1","request1",key])
            self.assertEqual((record["status"],record["score"],record["threshold"]),("incompatible",None,None))
        self.assertEqual(self.http(result+"wrong")[0],404)
        self.assertEqual(self.http(chat,body,{**headers,"X-Anchor-Session-Id":"another"})[0],400)
        # Hold one authenticated request open while checking independent HTTP routes.
        with socket.create_connection(("127.0.0.1", int(self.url.rsplit(":",1)[1])),timeout=2) as slow:
            host = self.url.removeprefix("http://")
            slow.sendall((f"POST {chat} HTTP/1.1\r\nHost: {host}\r\nAuthorization: Bearer {self.token}\r\n"
                          "Content-Length: 2\r\n\r\n{").encode())
            for _ in range(30):
                if self.http(chat,{})[0] == 503:
                    break
                time.sleep(0.02)
            else:
                self.fail("Provider did not report the competing request")
            self.assertEqual(self.http("/health")[1]["status"],"incompatible")
            slow.settimeout(0.05)
            with self.assertRaises(TimeoutError):
                slow.recv(1)
            slow.sendall(b"}")
            slow.settimeout(5)
            self.assertIn(b"400",slow.recv(256))
        self.process.kill()
        self.process.wait(timeout=30)
        with self.assertRaises((URLError, ConnectionError)):
            self.http(result+"call1")
        # Recovery must discard old in-memory records and report actual readiness.
        self.process.stdout.close()
        type(self).start()
        self.assertEqual(self.http(result+"call1")[0],404)
        api = json.loads((ROOT/"contracts/api.openapi.json").read_text())
        from referencing import Registry, Resource
        schema = validator.schema
        registry = Registry().with_resource(schema["$id"], Resource.from_contents(schema))
        for path in ("/health", "/metadata"):
            status, response = self.http(path)
            self.assertEqual(status, 200)
            shape = api["paths"][path]["get"]["responses"]["200"]["content"]["application/json"]["schema"]
            Draft202012Validator({**shape,"$id":"https://anchor.invalid/contracts/v1/api.openapi.json"},
                                 registry=registry).validate(response)
        self.assertEqual(self.http("/health")[1]["status"],"incompatible")


if __name__ == "__main__":
    unittest.main()
