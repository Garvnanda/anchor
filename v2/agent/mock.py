"""Local mock web + mailbox for the live agent (127.0.0.1 only). Serves one scenario's pages, a knowledge base,
an MCP-style tool list and files; records every mail it receives.

  GET  /page/<name>   text page            GET /kb?q=...   retrieval results (JSON)
  GET  /tools         tool list (JSON)     GET /file/<name> file text
  POST /mail          JSON {"to", "body"} → appended to the mailbox
"""
import http.server
import json
import threading
import urllib.parse


class MockWorld:
    def __init__(self, pages=None, kb=None, tools=None, files=None):
        self.pages = dict(pages or {})
        self.kb = kb
        self.tools = tools
        self.files = dict(files or {})
        self.mailbox = []
        self._server = None

    # --- server --------------------------------------------------------------------------------------------------

    def _handler(self):
        world = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def _send(self, code, body, ctype="text/plain; charset=utf-8"):
                data = body.encode("utf-8")
                self.send_response(code)
                self.send_header("content-type", ctype)
                self.send_header("content-length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self):  # noqa: N802
                url = urllib.parse.urlsplit(self.path)
                kind, _, name = url.path.strip("/").partition("/")
                name = urllib.parse.unquote(name)
                if kind == "page" and name in world.pages:
                    return self._send(200, world.pages[name])
                if kind == "file" and name in world.files:
                    return self._send(200, world.files[name])
                if kind == "kb" and world.kb is not None:
                    return self._send(200, world.kb, "application/json")
                if kind == "tools" and world.tools is not None:
                    return self._send(200, world.tools, "application/json")
                return self._send(404, "not found")

            def do_POST(self):  # noqa: N802
                if urllib.parse.urlsplit(self.path).path != "/mail":
                    return self._send(404, "not found")
                n = min(int(self.headers.get("content-length") or 0), 64 * 1024)
                try:
                    msg = json.loads(self.rfile.read(n).decode("utf-8"))
                    world.mailbox.append({"to": str(msg.get("to", "")), "body": str(msg.get("body", ""))})
                except (ValueError, AttributeError):
                    return self._send(400, "bad mail")
                return self._send(200, "sent")

            def log_message(self, *a):
                pass

        return Handler

    def start(self):
        self._server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), self._handler())
        threading.Thread(target=self._server.serve_forever, daemon=True).start()
        return self

    @property
    def base(self):
        return f"http://127.0.0.1:{self._server.server_address[1]}"

    def stop(self):
        if self._server:
            self._server.shutdown()
            self._server.server_close()

    def __enter__(self):
        return self.start()

    def __exit__(self, *exc):
        self.stop()
