from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


def utc_now() -> datetime:
    return datetime.now(UTC)


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class RunStatus(StrEnum):
    STARTED = "started"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass(frozen=True)
class Thread:
    id: str
    title: str = "New conversation"
    created_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True)
class Message:
    id: str
    thread_id: str
    role: MessageRole
    content: str
    created_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True)
class Attachment:
    id: str
    thread_id: str
    message_id: str | None
    original_filename: str
    mime_type: str
    size_bytes: int
    storage_uri: str
    agent_file_path: str
    created_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True)
class AgentRun:
    id: str
    thread_id: str
    triggering_message_id: str | None
    status: RunStatus
    started_at: datetime = field(default_factory=utc_now)
    finished_at: datetime | None = None
    error_message: str | None = None
    model_provider: str | None = None
    model_name: str | None = None


@dataclass(frozen=True)
class ToolCall:
    id: str
    agent_run_id: str
    tool_name: str
    input_summary: str
    output_summary: str
    status: RunStatus
    created_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True)
class ApprovalRequest:
    id: str
    thread_id: str
    agent_run_id: str | None
    requested_action: str
    preview: str
    status: ApprovalStatus = ApprovalStatus.PENDING
    created_at: datetime = field(default_factory=utc_now)
    decided_at: datetime | None = None


@dataclass(frozen=True)
class AgentResponse:
    content: str
    generated_files: list[str] = field(default_factory=list)
    pending_approval: ApprovalRequest | None = None
    plan: list[str] = field(default_factory=list)
