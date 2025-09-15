import os
from http.server import SimpleHTTPRequestHandler
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
