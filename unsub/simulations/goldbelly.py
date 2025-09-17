import os
from urllib.parse import parse_qs

from .base import AssetDir, BaseHandler, ServerSimulation, UnsubStatus


class GoldbellySimulation(ServerSimulation):
    def __init__(self):
        self._status: UnsubStatus = "failure"

    def start(self) -> str:
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

        return self.start_server(CustomHandler)

    def finish(self) -> UnsubStatus:
        self.stop_server()
        return self._status
