from sample_agents.domain.models import ApprovalRequest, ApprovalStatus, Message, MessageRole, new_id
from sample_agents.persistence.sqlite import SQLiteConversationRepository


def test_sqlite_repository_persists_messages(tmp_path):
    repo = SQLiteConversationRepository(f"sqlite:///{tmp_path / 'demo.db'}")
    thread = repo.create_thread("demo")
    message = Message(id=new_id("msg"), thread_id=thread.id, role=MessageRole.USER, content="hello")

    repo.save_message(message)

    assert repo.get_thread(thread.id).title == "demo"
    assert repo.list_messages(thread.id)[0].content == "hello"


def test_sqlite_approval_decision_is_atomic_and_idempotent(tmp_path):
    repo = SQLiteConversationRepository(f"sqlite:///{tmp_path / 'demo.db'}")
    thread = repo.create_thread("demo")
    approval = ApprovalRequest(
        id=new_id("approval"),
        thread_id=thread.id,
        agent_run_id="run_123",
        requested_action="send_customer_reply",
        preview="hello",
    )
    repo.save_approval(approval)

    first = repo.decide_approval(approval.id, ApprovalStatus.APPROVED)
    second = repo.decide_approval(approval.id, ApprovalStatus.APPROVED)

    assert first is not None
    assert first.status == ApprovalStatus.APPROVED
    assert second is None
    assert repo.get_approval(approval.id).status == ApprovalStatus.APPROVED
