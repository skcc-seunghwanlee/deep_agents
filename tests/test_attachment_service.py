from pathlib import Path

import pytest

from sample_agents.domain.models import new_id
from sample_agents.persistence.memory import InMemoryConversationRepository
from sample_agents.services.attachment_service import AttachmentService, safe_filename
from sample_agents.services.workspace import WorkspaceRegistry
from sample_agents.storage.local import LocalFileStorage


def test_safe_filename_removes_path_and_unsafe_chars():
    assert safe_filename("../my policy!!.md") == "my_policy__.md"


def test_attach_markdown_writes_workspace(tmp_path: Path):
    repo = InMemoryConversationRepository()
    thread = repo.create_thread()
    workspaces = WorkspaceRegistry()
    service = AttachmentService(repo, LocalFileStorage(tmp_path), workspaces)

    attachment = service.attach_bytes(thread.id, "policy.md", b"# Policy\nBody")

    assert attachment.agent_file_path == "/inputs/policy.md"
    assert workspaces.for_thread(thread.id).read("/inputs/policy.md") == "# Policy\nBody"
    assert repo.list_attachments(thread.id)[0].id == attachment.id


def test_attach_rejects_pdf(tmp_path: Path):
    repo = InMemoryConversationRepository()
    thread = repo.create_thread()
    service = AttachmentService(repo, LocalFileStorage(tmp_path), WorkspaceRegistry())

    with pytest.raises(ValueError, match="Only .md and .txt"):
        service.attach_bytes(thread.id, "policy.pdf", b"pdf")


def test_local_storage_with_relative_root_returns_file_uri(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    storage = LocalFileStorage(Path(".local_storage"))

    uri = storage.save_upload("thread-1", "policy.md", b"content")

    assert uri.startswith("file://")
    assert storage.read_uri(uri) == b"content"


def test_hydrate_workspace_restores_inputs_from_persisted_attachments(tmp_path: Path):
    from sample_agents.persistence.sqlite import SQLiteConversationRepository

    database_url = f"sqlite:///{tmp_path / 'demo.db'}"
    storage = LocalFileStorage(tmp_path / "storage")
    first_repo = SQLiteConversationRepository(database_url)
    thread = first_repo.create_thread()
    first_workspaces = WorkspaceRegistry()
    AttachmentService(first_repo, storage, first_workspaces).attach_bytes(thread.id, "a.md", b"# Policy")

    second_repo = SQLiteConversationRepository(database_url)
    second_workspaces = WorkspaceRegistry()
    service = AttachmentService(second_repo, storage, second_workspaces)

    assert second_workspaces.for_thread(thread.id).read("/inputs/a.md") is None
    assert service.hydrate_workspace(thread.id) == 1
    assert second_workspaces.for_thread(thread.id).read("/inputs/a.md") == "# Policy"
