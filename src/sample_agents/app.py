from dataclasses import asdict
from typing import Annotated

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from sample_agents.config import Settings, load_settings, validate_settings
from sample_agents.domain.models import ApprovalRequest, Attachment, Message, Thread
from sample_agents.integrations.models import model_info
from sample_agents.integrations.search_providers import create_search_provider
from sample_agents.persistence.memory import InMemoryConversationRepository
from sample_agents.persistence.repositories import ConversationRepository
from sample_agents.persistence.sqlite import SQLiteConversationRepository
from sample_agents.services.agent_service import AgentService
from sample_agents.services.approval_service import ApprovalService
from sample_agents.services.attachment_service import AttachmentService
from sample_agents.services.chat_service import ChatService
from sample_agents.services.workspace import WorkspaceRegistry
from sample_agents.storage.local import LocalFileStorage


class CreateThreadRequest(BaseModel):
    title: str = "New conversation"


class ThreadResponse(BaseModel):
    id: str
    title: str
    created_at: str


class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1)


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    created_at: str


class AgentMessageResponse(BaseModel):
    message: MessageResponse
    plan: list[str]
    generated_files: list[str]
    pending_approval: dict | None = None


class AttachmentResponse(BaseModel):
    id: str
    original_filename: str
    agent_file_path: str
    size_bytes: int


class WorkspaceFilesResponse(BaseModel):
    files: list[str]


class WorkspaceFileResponse(BaseModel):
    path: str
    content: str


class ApprovalDecisionRequest(BaseModel):
    approved: bool


class ApprovalDecisionResponse(BaseModel):
    result: str


class AppContainer:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        validate_settings(settings)
        if settings.database_url == "memory":
            self.repository: ConversationRepository = InMemoryConversationRepository()
        else:
            self.repository = SQLiteConversationRepository(settings.database_url)
        self.workspaces = WorkspaceRegistry()
        self.storage = LocalFileStorage(settings.local_storage_dir)
        self.search_provider = create_search_provider(settings.search_provider)
        self.agent_service = AgentService(settings, self.repository, self.workspaces, self.search_provider)
        self.chat_service = ChatService(self.repository, self.agent_service)
        self.attachment_service = AttachmentService(self.repository, self.storage, self.workspaces)
        self.approval_service = ApprovalService(self.repository)


def _thread_response(thread: Thread) -> ThreadResponse:
    return ThreadResponse(id=thread.id, title=thread.title, created_at=thread.created_at.isoformat())


def _message_response(message: Message) -> MessageResponse:
    return MessageResponse(
        id=message.id,
        role=message.role.value,
        content=message.content,
        created_at=message.created_at.isoformat(),
    )


def _attachment_response(attachment: Attachment) -> AttachmentResponse:
    return AttachmentResponse(
        id=attachment.id,
        original_filename=attachment.original_filename,
        agent_file_path=attachment.agent_file_path,
        size_bytes=attachment.size_bytes,
    )


def _approval_dict(approval: ApprovalRequest | None) -> dict | None:
    if approval is None:
        return None
    data = asdict(approval)
    data["status"] = approval.status.value
    data["created_at"] = approval.created_at.isoformat()
    data["decided_at"] = approval.decided_at.isoformat() if approval.decided_at else None
    return data


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    container = AppContainer(settings)
    app = FastAPI(title=settings.app_name, version="0.1.0")
    app.state.container = container

    def get_container() -> AppContainer:
        return app.state.container

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/model")
    def current_model(container: Annotated[AppContainer, Depends(get_container)]) -> dict[str, str]:
        return asdict(model_info(container.settings))

    @app.post("/threads", response_model=ThreadResponse)
    def create_thread(
        request: CreateThreadRequest,
        container: Annotated[AppContainer, Depends(get_container)],
    ) -> ThreadResponse:
        return _thread_response(container.chat_service.create_thread(request.title))

    @app.get("/threads/{thread_id}/messages", response_model=list[MessageResponse])
    def list_messages(thread_id: str, container: Annotated[AppContainer, Depends(get_container)]):
        try:
            return [_message_response(message) for message in container.chat_service.list_messages(thread_id)]
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/threads/{thread_id}/messages", response_model=AgentMessageResponse)
    def send_message(
        thread_id: str,
        request: SendMessageRequest,
        container: Annotated[AppContainer, Depends(get_container)],
    ) -> AgentMessageResponse:
        try:
            container.attachment_service.hydrate_workspace(thread_id)
            message, response = container.chat_service.handle_message(thread_id, request.content)
            return AgentMessageResponse(
                message=_message_response(message),
                plan=response.plan,
                generated_files=response.generated_files,
                pending_approval=_approval_dict(response.pending_approval),
            )
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/threads/{thread_id}/attachments", response_model=AttachmentResponse)
    async def upload_attachment(
        thread_id: str,
        file: Annotated[UploadFile, File()],
        container: Annotated[AppContainer, Depends(get_container)],
    ) -> AttachmentResponse:
        if container.repository.get_thread(thread_id) is None:
            raise HTTPException(status_code=404, detail=f"Thread not found: {thread_id}")
        content = await file.read()
        try:
            attachment = container.attachment_service.attach_bytes(thread_id, file.filename or "attachment.txt", content)
            return _attachment_response(attachment)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/threads/{thread_id}/workspace", response_model=WorkspaceFilesResponse)
    def list_workspace(thread_id: str, container: Annotated[AppContainer, Depends(get_container)]):
        if container.repository.get_thread(thread_id) is None:
            raise HTTPException(status_code=404, detail=f"Thread not found: {thread_id}")
        container.attachment_service.hydrate_workspace(thread_id)
        return WorkspaceFilesResponse(files=container.workspaces.for_thread(thread_id).list_paths())

    @app.get("/threads/{thread_id}/workspace/read", response_model=WorkspaceFileResponse)
    def read_workspace_file(
        thread_id: str,
        path: str,
        container: Annotated[AppContainer, Depends(get_container)],
    ) -> WorkspaceFileResponse:
        if container.repository.get_thread(thread_id) is None:
            raise HTTPException(status_code=404, detail=f"Thread not found: {thread_id}")
        container.attachment_service.hydrate_workspace(thread_id)
        content = container.workspaces.for_thread(thread_id).read(path)
        if content is None:
            raise HTTPException(status_code=404, detail=f"Workspace file not found: {path}")
        return WorkspaceFileResponse(path=path, content=content)

    @app.post("/approvals/{approval_id}/decision", response_model=ApprovalDecisionResponse)
    def decide_approval(
        approval_id: str,
        request: ApprovalDecisionRequest,
        container: Annotated[AppContainer, Depends(get_container)],
    ) -> ApprovalDecisionResponse:
        try:
            return ApprovalDecisionResponse(result=container.approval_service.decide(approval_id, request.approved))
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    return app


app = create_app()
