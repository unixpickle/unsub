import os
import socket
import threading
from http.server import HTTPServer

from .base import AssetDir, BaseHandler, UnsubStatus


class SingleStepSimulation:
    def __init__(self, index_page: str):
        self.index_page = index_page
        self.httpd: HTTPServer | None = None
        self.thread: threading.Thread | None = None
        self.port: int | None = None
        self._status: UnsubStatus = "failure"

    def start(self) -> str:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("", 0))
        self.port = sock.getsockname()[1]
        sock.close()

        index_page = self.index_page
        asset_root = os.path.abspath(AssetDir)
        parent = self

        class CustomHandler(BaseHandler):
            def translate_path(self, path: str) -> str:
                # Remove query/fragment
                path = path.split("?", 1)[0].split("#", 1)[0]

                if path == "/":
                    return os.path.join(asset_root, index_page)

                if path == "/unsubscribe":
                    parent._status = "success"
                    return os.path.join(asset_root, "unsubscribed.html")

                if path == "/staysubscribed":
                    parent._status = "failure"
                    return os.path.join(asset_root, "staysubscribed.html")

                if path in ("/updated_failure", "/updated_success"):
                    parent._status = (
                        "failure" if path == "/updated_failure" else "success"
                    )
                    return os.path.join(asset_root, "updated.html")

                # Normalize and sandbox
                rel_path = path.lstrip("/")
                safe_path = os.path.normpath(os.path.join(asset_root, rel_path))

                # Ensure final path stays inside asset_root
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
        if self._status == "success":
            return "success"
        elif self._status == "failure":
            return "failure"
        else:
            return "failure"  # no decisive action taken
