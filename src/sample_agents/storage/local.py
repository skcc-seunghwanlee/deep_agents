from __future__ import annotations

from pathlib import Path
from urllib.parse import unquote, urlparse
from uuid import uuid4


class LocalFileStorage:
    def __init__(self, root: Path) -> None:
        self.root = root.expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def save_upload(self, thread_id: str, filename: str, content: bytes) -> str:
        directory = self.root / thread_id / "originals"
        directory.mkdir(parents=True, exist_ok=True)
        path = self._unique_path(directory, filename)
        path.write_bytes(content)
        return path.as_uri()

    def read_uri(self, storage_uri: str) -> bytes:
        return self.uri_to_path(storage_uri).read_bytes()

    def uri_to_path(self, storage_uri: str) -> Path:
        if not storage_uri.startswith("file://"):
            raise ValueError("LocalFileStorage only supports file:// URIs")
        parsed = urlparse(storage_uri)
        return Path(unquote(parsed.path))

    def _unique_path(self, directory: Path, filename: str) -> Path:
        candidate = (directory / filename).resolve()
        if not candidate.exists():
            return candidate
        stem = Path(filename).stem
        suffix = Path(filename).suffix
        return (directory / f"{stem}_{uuid4().hex[:8]}{suffix}").resolve()
