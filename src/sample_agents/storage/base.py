from __future__ import annotations

from pathlib import Path
from typing import Protocol


class FileStorage(Protocol):
    def save_upload(self, thread_id: str, filename: str, content: bytes) -> str: ...
    def read_uri(self, storage_uri: str) -> bytes: ...
    def uri_to_path(self, storage_uri: str) -> Path: ...
