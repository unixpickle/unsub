import os

from .base import (
    AssetDir,
    BaseHandler,
    ServerSimulation,
    UnsubStatus,
    parse_path_and_query,
)


class PecoSimulation(ServerSimulation):
    def __init__(self):
        self._status: UnsubStatus = "failure"

    def start(self) -> str:
        asset_root = os.path.abspath(AssetDir)
        parent = self

        class CustomHandler(BaseHandler):
            def translate_path(self, path: str) -> str:
                path, query = parse_path_and_query(path)

                if path == "/":
                    return os.path.join(asset_root, "peco", "index.html")

                if path == "/update_preferences":
                    parent._status = (
                        "success"
                        if all(
                            query.get(str(i), [""]) == [""]
                            for i in (19, 22, 18, 9, 10, 14, 23, 25, 17, 26)
                        )
                        else "failure"
                    )
                    return os.path.join(asset_root, "updated.html")

                rel_path = path.lstrip("/")
                safe_path = os.path.normpath(os.path.join(asset_root, "peco", rel_path))

                if not safe_path.startswith(asset_root + os.sep):
                    return os.path.join(asset_root, "404.html")

                return safe_path

        return self.start_server(CustomHandler)

    def finish(self) -> UnsubStatus:
        self.stop_server()
        return self._status
