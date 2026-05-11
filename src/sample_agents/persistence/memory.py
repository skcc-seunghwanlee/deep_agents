from __future__ import annotations

from dataclasses import replace

from sample_agents.domain.models import (
    AgentRun,
    ApprovalRequest,
    ApprovalStatus,
    Attachment,
    Message,
    Thread,
    ToolCall,
    new_id,
    utc_now,
)


class InMemoryConversationRepository:
    def __init__(self) -> None:
        self.threads: dict[str, Thread] = {}
        self.messages: list[Message] = []
        self.attachments: list[Attachment] = []
        self.runs: dict[str, AgentRun] = {}
        self.tool_calls: list[ToolCall] = []
        self.approvals: dict[str, ApprovalRequest] = {}

    def create_thread(self, title: str = "New conversation") -> Thread:
        thread = Thread(id=new_id("thread"), title=title)
        self.threads[thread.id] = thread
        return thread

    def get_thread(self, thread_id: str) -> Thread | None:
        return self.threads.get(thread_id)

    def save_message(self, message: Message) -> None:
        self.messages.append(message)

    def list_messages(self, thread_id: str) -> list[Message]:
        return [message for message in self.messages if message.thread_id == thread_id]

    def save_attachment(self, attachment: Attachment) -> None:
        self.attachments.append(attachment)

    def list_attachments(self, thread_id: str) -> list[Attachment]:
        return [attachment for attachment in self.attachments if attachment.thread_id == thread_id]

    def save_agent_run(self, run: AgentRun) -> None:
        self.runs[run.id] = run

    def update_agent_run(self, run: AgentRun) -> None:
        self.runs[run.id] = run

    def save_tool_call(self, call: ToolCall) -> None:
        self.tool_calls.append(call)

    def save_approval(self, approval: ApprovalRequest) -> None:
        self.approvals[approval.id] = approval

    def get_pending_approval(self, thread_id: str) -> ApprovalRequest | None:
        for approval in self.approvals.values():
            if approval.thread_id == thread_id and approval.status == ApprovalStatus.PENDING:
                return approval
        return None

    def decide_approval(self, approval_id: str, status: ApprovalStatus) -> ApprovalRequest | None:
        approval = self.approvals.get(approval_id)
        if approval is None:
            return None
        decided = replace(approval, status=status, decided_at=utc_now())
        self.approvals[approval_id] = decided
        return decided
