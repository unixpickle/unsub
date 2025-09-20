import os

from .base import (
    AssetDir,
    BaseHandler,
    ServerSimulation,
    UnsubStatus,
    parse_path_and_query,
)


class FandangoSimulation(ServerSimulation):
    def __init__(self):
        self._status: UnsubStatus = "failure"

    def start(self) -> str:
        asset_root = os.path.abspath(AssetDir)
        parent = self

        class CustomHandler(BaseHandler):
            def translate_path(self, path: str) -> str:
                path, query = parse_path_and_query(path)

                if path == "/":
                    return os.path.join(asset_root, "fandango.html")

                if path == "/update_preferences":
                    parent._status = (
                        "success"
                        if all(query.get(f"sub{i}") is None for i in (1, 2, 3))
                        else "failure"
                    )
                    return os.path.join(asset_root, "updated.html")
                elif path == "/unsubscribe_all":
                    parent._status = "success"
                    return os.path.join(asset_root, "updated.html")
                elif path == "/homepage":
                    parent._status = "failure"
                    return os.path.join(asset_root, "404.html")

                rel_path = path.lstrip("/")
                safe_path = os.path.normpath(os.path.join(asset_root, rel_path))

                if not safe_path.startswith(asset_root + os.sep):
                    return os.path.join(asset_root, "404.html")

                return safe_path

        return self.start_server(CustomHandler)

    def finish(self) -> UnsubStatus:
        self.stop_server()
        return self._status
