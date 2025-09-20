import os

from .base import (
    AssetDir,
    BaseHandler,
    ServerSimulation,
    UnsubStatus,
    parse_path_and_query,
)


class HoneywellSimulation(ServerSimulation):
    def __init__(self):
        self._status: UnsubStatus = "failure"

    def start(self) -> str:
        asset_root = os.path.abspath(AssetDir)
        parent = self

        class CustomHandler(BaseHandler):
            def translate_path(self, path: str) -> str:
                path, query = parse_path_and_query(path)

                if path == "/":
                    return os.path.join(asset_root, "honeywell", "index.html")

                if path == "/update_preferences":
                    parent._status = (
                        "success"
                        if query.get("items[unsuball]") == ["unsuball"]
                        else "failure"
                    )
                    return os.path.join(asset_root, "updated.html")

                if path == "/homepage":
                    parent._status = "failure"
                    return os.path.join(asset_root, "honeywell", "homepage.html")

                rel_path = path.lstrip("/")
                safe_path = os.path.normpath(
                    os.path.join(asset_root, "honeywell", rel_path)
                )

                if not safe_path.startswith(asset_root + os.sep):
                    return os.path.join(asset_root, "404.html")

                return safe_path

        return self.start_server(CustomHandler)

    def finish(self) -> UnsubStatus:
        self.stop_server()
        return self._status
