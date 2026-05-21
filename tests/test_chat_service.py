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
