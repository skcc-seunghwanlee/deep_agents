from sample_agents.domain.models import ApprovalRequest, ApprovalStatus, new_id
from sample_agents.persistence.memory import InMemoryConversationRepository
from sample_agents.services.approval_service import ApprovalService


def test_approval_decision_is_idempotent_after_approval():
    repo = InMemoryConversationRepository()
    thread = repo.create_thread()
    approval = ApprovalRequest(
        id=new_id("approval"),
        thread_id=thread.id,
        agent_run_id="run_123",
        requested_action="send_customer_reply",
        preview="hello",
    )
    repo.save_approval(approval)
    service = ApprovalService(repo)

    first = service.decide(approval.id, approved=True)
    second = service.decide(approval.id, approved=True)

    assert "Mock send completed" in first
    assert "이미 처리된 승인 요청" in second
    assert repo.get_approval(approval.id).status == ApprovalStatus.APPROVED
    assert len(repo.tool_calls) == 1


def test_rejected_approval_cannot_be_approved_later():
    repo = InMemoryConversationRepository()
    thread = repo.create_thread()
    approval = ApprovalRequest(
        id=new_id("approval"),
        thread_id=thread.id,
        agent_run_id="run_123",
        requested_action="send_customer_reply",
        preview="hello",
    )
    repo.save_approval(approval)
    service = ApprovalService(repo)

    rejected = service.decide(approval.id, approved=False)
    retried = service.decide(approval.id, approved=True)

    assert "거절" in rejected
    assert "이미 처리된 승인 요청" in retried
    assert repo.get_approval(approval.id).status == ApprovalStatus.REJECTED
    assert len(repo.tool_calls) == 0
