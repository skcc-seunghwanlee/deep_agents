from __future__ import annotations

from pathlib import Path


class LocalFileStorage:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def save_upload(self, thread_id: str, filename: str, content: bytes) -> str:
        directory = self.root / thread_id / "originals"
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / filename
        path.write_bytes(content)
        return path.as_uri()

    def read_uri(self, storage_uri: str) -> bytes:
        return self.uri_to_path(storage_uri).read_bytes()

    def uri_to_path(self, storage_uri: str) -> Path:
        if not storage_uri.startswith("file://"):
            raise ValueError("LocalFileStorage only supports file:// URIs")
        return Path(storage_uri.removeprefix("file://"))
