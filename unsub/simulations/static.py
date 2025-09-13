import os
import socket
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler

from .base import AssetDir, UnsubStatus


class StaticSimulation:
    def __init__(self, index_page: str):
        self.index_page = index_page
        self.httpd: HTTPServer | None = None
        self.thread: threading.Thread | None = None
        self.port: int | None = None

    def start(self) -> str:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("", 0))
        self.port = sock.getsockname()[1]
        sock.close()

        index_page = self.index_page
        asset_root = os.path.abspath(AssetDir)

        class CustomHandler(SimpleHTTPRequestHandler):
            def translate_path(self, path: str) -> str:
                # Remove query/fragment
                path = path.split("?", 1)[0].split("#", 1)[0]

                if path == "/":
                    return os.path.join(asset_root, index_page)

                # Normalize and sandbox
                rel_path = path.lstrip("/")
                safe_path = os.path.normpath(os.path.join(asset_root, rel_path))

                # Ensure final path stays inside asset_root
                if not safe_path.startswith(asset_root + "/"):
                    return os.path.join(asset_root, "404.html")

                return safe_path

            def log_message(self, format, *args):
                pass  # silence logs

            def end_headers(self):
                # Prevent shutdown / server_close from hanging.
                self.send_header("Connection", "close")
                super().end_headers()

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
        return "success"
