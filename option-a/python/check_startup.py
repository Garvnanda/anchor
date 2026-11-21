"""Cold-start the managed provider and verify the HTTP compatibility boundary."""
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
from urllib.error import HTTPError
from urllib.request import Request, urlopen

def main():
    token = secrets.token_urlsafe(32)
    process = subprocess.Popen([sys.executable, "-B", str(Path(__file__).with_name("serve.py"))],
                               stdout=subprocess.PIPE, text=True, env={**os.environ,"ANCHOR_DETECTOR_TOKEN":token})
    try:
        port = json.loads(process.stdout.readline())["port"]
        for path, credential, status, key, value in [
            ("/health", "", 401, "errorCode", "UNAUTHORIZED"),
            ("/health", token, 200, "status", "incompatible"),
            ("/metadata", token, 200, "provenance", None),
            ("/v1/activations/missing?toolCallId=call",token,404,"errorCode","NO_COMPATIBLE_ACTIVATION"),
            ("/v1/models",token,200,"object","list"),
        ]:
            request = Request(f"http://127.0.0.1:{port}"+path, headers={"Authorization":"Bearer "+credential})
            try:
                response = urlopen(request, timeout=15)
            except HTTPError as error:
                response = error
            with response:
                assert response.status == status
                assert json.load(response)[key] == value
        base_url = f"http://127.0.0.1:{port}"
        headers = {"Authorization": "Bearer " + token, "Content-Type": "application/json"}
        for request, expected in [
            (Request(base_url + "/health", headers={**headers, "Origin": "http://example.invalid"}), 403),
            (Request(base_url + "/health", headers={**headers, "Host": "example.invalid"}), 403),
            (Request(base_url + "/v1/chat/completions", data=b"{", headers=headers), 400),
        ]:
            try:
                urlopen(request, timeout=15).close()
            except HTTPError as error:
                with error:
                    assert error.code == expected
            else:
                raise AssertionError(f"Expected HTTP {expected}")
        print("Managed startup and eight HTTP checks passed")
    finally:
        process.terminate()
        process.wait(timeout=30)

if __name__=="__main__":
    main()
