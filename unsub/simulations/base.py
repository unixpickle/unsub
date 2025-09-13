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
