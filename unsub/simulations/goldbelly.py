import os
import socket
import threading
from http.server import HTTPServer
from urllib.parse import parse_qs

from .base import AssetDir, BaseHandler, UnsubStatus


class GoldbellySimulation:
    def __init__(self):
        self.httpd: HTTPServer | None = None
        self.thread: threading.Thread | None = None
        self.port: int | None = None
        self._status: UnsubStatus = "failure"

    def start(self) -> str:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("", 0))
        self.port = sock.getsockname()[1]
        sock.close()

        asset_root = os.path.abspath(AssetDir)
        parent = self

        class CustomHandler(BaseHandler):
            def translate_path(self, path: str) -> str:
                # Remove query/fragment
                path = path.split("#")[0]
                if len(parts := path.split("?")) > 1:
                    path = parts[0]
                    query = parse_qs(parts[1])
                else:
                    query = {}

                if path == "/":
                    return os.path.join(asset_root, "goldbelly", "index.html")

                if path == "/email_preferences":
                    parent._status = (
                        "success"
                        if query["user[unsubscribed]"] == ["true"]
                        else "failure"
                    )
                    return os.path.join(asset_root, "updated.html")

                if path == "/homepage":
                    parent._status = "failure"
                    return os.path.join(asset_root, "goldbelly", "homepage.html")

                rel_path = path.lstrip("/")
                safe_path = os.path.normpath(
                    os.path.join(asset_root, "goldbelly", rel_path)
                )

                if not safe_path.startswith(asset_root + os.sep):
                    return os.path.join(asset_root, "404.html")

                return safe_path

        self.httpd = HTTPServer(("127.0.0.1", self.port), CustomHandler)  # type: ignore

        def run_server():
            assert self.httpd is not None
            self.httpd.serve_forever()

        self.thread = threading.Thread(target=run_server, daemon=True)
        self.thread.start()

        return f"http://127.0.0.1:{self.port}/"

    def finish(self) -> UnsubStatus:
        if self.httpd:
            assert self.thread is not None
            self.httpd.shutdown()
            self.httpd.server_close()
            self.thread.join(timeout=1)

        # Default to "success" only if unsub was reached
        return self._status
