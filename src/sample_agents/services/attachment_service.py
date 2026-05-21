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
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("첨부 파일은 UTF-8 텍스트(.md/.txt)만 지원합니다.") from exc
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

    def hydrate_workspace(self, thread_id: str) -> int:
        workspace = self.workspaces.for_thread(thread_id)
        hydrated = 0
        for attachment in self.repository.list_attachments(thread_id):
            if not attachment.agent_file_path.startswith("/inputs/"):
                continue
            if workspace.read(attachment.agent_file_path) is not None:
                continue
            try:
                text = self.storage.read_uri(attachment.storage_uri).decode("utf-8")
            except UnicodeDecodeError:
                # 기존 데이터 중 디코딩 불가 파일은 복원 대상에서 건너뜁니다.
                continue
            workspace.write(attachment.agent_file_path, text)
            hydrated += 1
        return hydrated
