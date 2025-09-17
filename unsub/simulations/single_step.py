import os

from .base import AssetDir, BaseHandler, ServerSimulation, UnsubStatus


class SingleStepSimulation(ServerSimulation):
    def __init__(self, index_page: str):
        self.index_page = index_page
        self._status: UnsubStatus = "failure"

    def start(self) -> str:
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

        return self.start_server(CustomHandler)

    def finish(self) -> UnsubStatus:
        self.stop_server()
        return self._status
