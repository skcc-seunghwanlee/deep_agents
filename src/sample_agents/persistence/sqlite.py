from __future__ import annotations

import sqlite3
from dataclasses import replace
from datetime import datetime
from pathlib import Path

from sample_agents.domain.models import (
    AgentRun,
    ApprovalRequest,
    ApprovalStatus,
    Attachment,
    Message,
    MessageRole,
    RunStatus,
    Thread,
    ToolCall,
    new_id,
    utc_now,
)


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


class SQLiteConversationRepository:
    def __init__(self, database_url: str) -> None:
        if not database_url.startswith("sqlite:///"):
            raise ValueError("This sample SQLite repository expects DATABASE_URL like sqlite:///./demo.db")
        self.path = Path(database_url.removeprefix("sqlite:///"))
        if self.path.parent != Path(""):
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        schema = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
        with self._connect() as connection:
            connection.executescript(schema)

    def create_thread(self, title: str = "New conversation") -> Thread:
        thread = Thread(id=new_id("thread"), title=title)
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO agent_threads (id, title, created_at) VALUES (?, ?, ?)",
                (thread.id, thread.title, thread.created_at.isoformat()),
            )
        return thread

    def get_thread(self, thread_id: str) -> Thread | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM agent_threads WHERE id = ?", (thread_id,)).fetchone()
        if row is None:
            return None
        return Thread(id=row["id"], title=row["title"], created_at=_dt(row["created_at"]))

    def save_message(self, message: Message) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO messages (id, thread_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)",
                (message.id, message.thread_id, message.role.value, message.content, message.created_at.isoformat()),
            )

    def list_messages(self, thread_id: str) -> list[Message]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM messages WHERE thread_id = ? ORDER BY created_at ASC", (thread_id,)
            ).fetchall()
        return [
            Message(
                id=row["id"],
                thread_id=row["thread_id"],
                role=MessageRole(row["role"]),
                content=row["content"],
                created_at=_dt(row["created_at"]),
            )
            for row in rows
        ]

    def save_attachment(self, attachment: Attachment) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO message_attachments
                (id, thread_id, message_id, original_filename, mime_type, size_bytes, storage_uri, agent_file_path, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    attachment.id,
                    attachment.thread_id,
                    attachment.message_id,
                    attachment.original_filename,
                    attachment.mime_type,
                    attachment.size_bytes,
                    attachment.storage_uri,
                    attachment.agent_file_path,
                    attachment.created_at.isoformat(),
                ),
            )

    def list_attachments(self, thread_id: str) -> list[Attachment]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM message_attachments WHERE thread_id = ? ORDER BY created_at ASC", (thread_id,)
            ).fetchall()
        return [
            Attachment(
                id=row["id"],
                thread_id=row["thread_id"],
                message_id=row["message_id"],
                original_filename=row["original_filename"],
                mime_type=row["mime_type"],
                size_bytes=row["size_bytes"],
                storage_uri=row["storage_uri"],
                agent_file_path=row["agent_file_path"],
                created_at=_dt(row["created_at"]),
            )
            for row in rows
        ]

    def save_agent_run(self, run: AgentRun) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO agent_runs
                (id, thread_id, triggering_message_id, status, started_at, finished_at, error_message, model_provider, model_name)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run.id,
                    run.thread_id,
                    run.triggering_message_id,
                    run.status.value,
                    run.started_at.isoformat(),
                    run.finished_at.isoformat() if run.finished_at else None,
                    run.error_message,
                    run.model_provider,
                    run.model_name,
                ),
            )

    def update_agent_run(self, run: AgentRun) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE agent_runs
                SET status = ?, finished_at = ?, error_message = ?, model_provider = ?, model_name = ?
                WHERE id = ?
                """,
                (
                    run.status.value,
                    run.finished_at.isoformat() if run.finished_at else None,
                    run.error_message,
                    run.model_provider,
                    run.model_name,
                    run.id,
                ),
            )

    def save_tool_call(self, call: ToolCall) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO tool_calls (id, agent_run_id, tool_name, input_summary, output_summary, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    call.id,
                    call.agent_run_id,
                    call.tool_name,
                    call.input_summary,
                    call.output_summary,
                    call.status.value,
                    call.created_at.isoformat(),
                ),
            )

    def save_approval(self, approval: ApprovalRequest) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO approvals (id, thread_id, agent_run_id, requested_action, preview, status, created_at, decided_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    approval.id,
                    approval.thread_id,
                    approval.agent_run_id,
                    approval.requested_action,
                    approval.preview,
                    approval.status.value,
                    approval.created_at.isoformat(),
                    approval.decided_at.isoformat() if approval.decided_at else None,
                ),
            )

    def get_approval(self, approval_id: str) -> ApprovalRequest | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM approvals WHERE id = ?", (approval_id,)).fetchone()
        if row is None:
            return None
        return ApprovalRequest(
            id=row["id"],
            thread_id=row["thread_id"],
            agent_run_id=row["agent_run_id"],
            requested_action=row["requested_action"],
            preview=row["preview"],
            status=ApprovalStatus(row["status"]),
            created_at=_dt(row["created_at"]),
            decided_at=_dt(row["decided_at"]) if row["decided_at"] else None,
        )

    def get_pending_approval(self, thread_id: str) -> ApprovalRequest | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM approvals WHERE thread_id = ? AND status = ? ORDER BY created_at DESC LIMIT 1",
                (thread_id, ApprovalStatus.PENDING.value),
            ).fetchone()
        if row is None:
            return None
        return ApprovalRequest(
            id=row["id"],
            thread_id=row["thread_id"],
            agent_run_id=row["agent_run_id"],
            requested_action=row["requested_action"],
            preview=row["preview"],
            status=ApprovalStatus(row["status"]),
            created_at=_dt(row["created_at"]),
            decided_at=_dt(row["decided_at"]) if row["decided_at"] else None,
        )

    def decide_approval(self, approval_id: str, status: ApprovalStatus) -> ApprovalRequest | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM approvals WHERE id = ?", (approval_id,)).fetchone()
            if row is None or ApprovalStatus(row["status"]) != ApprovalStatus.PENDING:
                return None
            pending = ApprovalRequest(
                id=row["id"],
                thread_id=row["thread_id"],
                agent_run_id=row["agent_run_id"],
                requested_action=row["requested_action"],
                preview=row["preview"],
                status=ApprovalStatus(row["status"]),
                created_at=_dt(row["created_at"]),
                decided_at=_dt(row["decided_at"]) if row["decided_at"] else None,
            )
            decided = replace(pending, status=status, decided_at=utc_now())
            connection.execute(
                "UPDATE approvals SET status = ?, decided_at = ? WHERE id = ?",
                (decided.status.value, decided.decided_at.isoformat(), approval_id),
            )
            return decided
