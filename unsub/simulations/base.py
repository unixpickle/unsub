import os
import socket
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
from typing import Literal, Protocol

UnsubStatus = Literal["success", "failure"]
AssetDir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")


class Simulation(Protocol):
    def start(self) -> str:
        """Start the simulation and return a URL."""
        ...

    def finish(self) -> UnsubStatus:
        """Start the simulation and return a URL."""
        ...


class BaseHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        # Silence logs
        pass

    def end_headers(self):
        # Prevent shutdown / server_close from hanging.
        self.send_header("Connection", "close")
        super().end_headers()

    def setup(self):
        super().setup()
        try:
            self.request.settimeout(2)  # avoid open sockets preventing shutdown
        except Exception:
            pass


class ServerSimulation:
    def __init__(self):
        self.httpd: HTTPServer | None = None
        self.thread: threading.Thread | None = None

    def compute_port(self) -> int:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("", 0))
        port = sock.getsockname()[1]
        sock.close()
        return port

    def start_server(self, handler: type[SimpleHTTPRequestHandler]) -> str:
        port = self.compute_port()
        self.httpd = HTTPServer(("127.0.0.1", port), handler)  # type: ignore

        def run_server():
            assert self.httpd is not None
            self.httpd.serve_forever()

        self.thread = threading.Thread(target=run_server, daemon=True)
        self.thread.start()

        return f"http://127.0.0.1:{port}/"

    def stop_server(self):
        if self.httpd:
            assert self.thread is not None
            self.httpd.shutdown()
            self.httpd.server_close()
            self.thread.join(timeout=1)
