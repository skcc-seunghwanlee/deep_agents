from sample_agents.agents.subagents import DOCUMENT_READER, RISK_REVIEWER
import pytest
from sample_agents.config import Settings
from sample_agents.integrations.search_providers import MockSearchProvider
from sample_agents.persistence.memory import InMemoryConversationRepository
from sample_agents.services.agent_service import AgentService
from sample_agents.services.attachment_service import AttachmentService
from sample_agents.services.chat_service import ChatService
from sample_agents.services.workspace import WorkspaceRegistry
from sample_agents.storage.local import LocalFileStorage


def test_chat_service_generates_workspace_files(tmp_path):
    settings = Settings(model_provider="fake", model_name="fake")
    repo = InMemoryConversationRepository()
    workspaces = WorkspaceRegistry()
    thread = repo.create_thread()
    AttachmentService(repo, LocalFileStorage(tmp_path), workspaces).attach_bytes(
        thread.id,
        "policy.md",
        "# 정책\n개인정보 보관 기간과 제3자 제공을 안내합니다.".encode(),
    )
    chat = ChatService(repo, AgentService(settings, repo, workspaces, MockSearchProvider()))

    message, response = chat.handle_message(thread.id, "요약하고 리스크와 고객 답변 초안을 만들어줘")

    assert message.role.value == "assistant"
    assert "/outputs/summary.md" in response.generated_files
    assert "/outputs/customer_reply.md" in response.generated_files
    assert workspaces.for_thread(thread.id).read("/outputs/risks.md") is not None
    assert len(repo.list_messages(thread.id)) == 2


def test_agent_run_marks_failed_on_exception(tmp_path, monkeypatch):
    settings = Settings(model_provider="fake", model_name="fake")
    repo = InMemoryConversationRepository()
    workspaces = WorkspaceRegistry()
    thread = repo.create_thread()
    AttachmentService(repo, LocalFileStorage(tmp_path), workspaces).attach_bytes(
        thread.id,
        "policy.md",
        "# 정책\n개인정보 보관 기간".encode(),
    )
    agent = AgentService(settings, repo, workspaces, MockSearchProvider())

    def _boom(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(agent, "_run_fake_document_agent", _boom)

    with pytest.raises(RuntimeError, match="boom"):
        agent.run(thread.id, "msg_trigger", "요약해줘")

    last_run = list(repo.runs.values())[-1]
    assert last_run.status.value == "failed"
    assert last_run.error_message == "boom"
    assert last_run.finished_at is not None


def test_subagents_include_system_prompt():
    assert DOCUMENT_READER["system_prompt"]
    assert RISK_REVIEWER["system_prompt"]
