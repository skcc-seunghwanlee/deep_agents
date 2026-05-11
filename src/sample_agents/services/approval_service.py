from __future__ import annotations

from sample_agents.domain.models import ApprovalStatus, RunStatus, ToolCall, new_id
from sample_agents.persistence.repositories import ConversationRepository
from sample_agents.tools.customer_reply import send_customer_reply


class ApprovalService:
    def __init__(self, repository: ConversationRepository) -> None:
        self.repository = repository

    def decide(self, approval_id: str, approved: bool) -> str:
        status = ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED
        approval = self.repository.decide_approval(approval_id, status)
        if approval is None:
            raise ValueError(f"Approval not found: {approval_id}")
        if not approved:
            return "승인이 거절되어 작업을 실행하지 않았습니다."
        result = send_customer_reply(approval.preview)
        if approval.agent_run_id is not None:
            self.repository.save_tool_call(
                ToolCall(
                    id=new_id("tool"),
                    agent_run_id=approval.agent_run_id,
                    tool_name="send_customer_reply",
                    input_summary=approval.preview[:200],
                    output_summary=result,
                    status=RunStatus.SUCCEEDED,
                )
            )
        return result
