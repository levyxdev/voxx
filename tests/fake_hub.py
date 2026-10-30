"""A local stand-in for Hugging Face, reached through HF_ENDPOINT: the tree API and `resolve/` downloads, nothing else."""

import hashlib
import json
import re
import threading
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


@dataclass
class Request:
    path: str
    range: str | None


@dataclass
class FakeHub:
    # (repo, revision) -> {file path: content}
    repos: dict = field(default_factory=dict)
    requests: list = field(default_factory=list)
    # file path -> bytes sent before the connection drops, once
    cut_after: dict = field(default_factory=dict)
    # file paths served with one byte changed
    corrupt: set = field(default_factory=set)
    # file path -> size the tree API reports instead of the real one
    reported_sizes: dict = field(default_factory=dict)

    def start(self):
        hub = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                hub.requests.append(Request(self.path, self.headers.get("Range")))
                hub._handle(self)

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        return self

    def stop(self):
        self.server.shutdown()
        self.server.server_close()

    def _handle(self, handler):
        path = handler.path.split("?")[0]
        for (repo, revision), files in self.repos.items():
            if path == f"/api/models/{repo}/tree/{revision}":
                return _send(handler, 200, json.dumps([self._tree_entry(p, c) for p, c in files.items()]).encode())
            prefix = f"/{repo}/resolve/{revision}/"
            if path.startswith(prefix) and path[len(prefix):] in files:
                return self._download(handler, path[len(prefix):], files[path[len(prefix):]])
        _send(handler, 404, b'{"error": "Entry not found"}')

    def _tree_entry(self, path, content):
        size = self.reported_sizes.get(path, len(content))
        entry = {"type": "file", "path": path, "size": size,
                 "oid": hashlib.sha1(b"blob %d\0" % len(content) + content).hexdigest()}
        if path.endswith(".safetensors"):
            entry["lfs"] = {"oid": hashlib.sha256(content).hexdigest(), "size": size, "pointerSize": 134}
        return entry

    def _download(self, handler, path, content):
        if path in self.corrupt:
            content = bytes([content[0] ^ 0xFF]) + content[1:]
        start = 0
        match = re.fullmatch(r"bytes=(\d+)-", handler.headers.get("Range") or "")
        if match:
            start = int(match.group(1))
            handler.send_response(206)
            handler.send_header("Content-Range", f"bytes {start}-{len(content) - 1}/{len(content)}")
        else:
            handler.send_response(200)
        handler.send_header("Content-Length", str(len(content) - start))
        handler.end_headers()
        body = content[start:]
        if path in self.cut_after:
            body = body[:self.cut_after.pop(path)]
            handler.wfile.write(body)
            handler.wfile.flush()
            handler.close_connection = True
            return
        handler.wfile.write(body)


def _send(handler, status, body):
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)
