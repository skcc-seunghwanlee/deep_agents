from __future__ import annotations

import mimetypes
import re
from pathlib import Path

from sample_agents.domain.models import Attachment, new_id
from sample_agents.persistence.repositories import ConversationRepository
from sample_agents.services.workspace import WorkspaceRegistry
from sample_agents.storage.base import FileStorage

_ALLOWED_SUFFIXES = {".md", ".txt"}


def safe_filename(filename: str) -> str:
    name = Path(filename).name
    return re.sub(r"[^A-Za-z0-9._-]", "_", name)


class AttachmentService:
    def __init__(
        self,
        repository: ConversationRepository,
        storage: FileStorage,
        workspaces: WorkspaceRegistry,
    ) -> None:
        self.repository = repository
        self.storage = storage
        self.workspaces = workspaces

    def attach_bytes(
        self,
        thread_id: str,
        filename: str,
        content: bytes,
        message_id: str | None = None,
    ) -> Attachment:
        safe_name = safe_filename(filename)
        suffix = Path(safe_name).suffix.lower()
        if suffix not in _ALLOWED_SUFFIXES:
            raise ValueError("Only .md and .txt attachments are supported in the sample MVP.")
        text = content.decode("utf-8")
        storage_uri = self.storage.save_upload(thread_id, safe_name, content)
        agent_file_path = f"/inputs/{safe_name}"
        self.workspaces.for_thread(thread_id).write(agent_file_path, text)
        attachment = Attachment(
            id=new_id("att"),
            thread_id=thread_id,
            message_id=message_id,
            original_filename=safe_name,
            mime_type=mimetypes.guess_type(safe_name)[0] or "text/plain",
            size_bytes=len(content),
            storage_uri=storage_uri,
            agent_file_path=agent_file_path,
        )
        self.repository.save_attachment(attachment)
        return attachment
