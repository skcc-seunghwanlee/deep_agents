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
    title: str = Field(default="New conversation", description="새 대화방 제목입니다.")


class ThreadResponse(BaseModel):
    id: str
    title: str
    created_at: str


class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1, description="에이전트에게 보낼 사용자 메시지입니다.")


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
    approved: bool = Field(description="승인 여부입니다. true면 실행, false면 거절합니다.")


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
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description=(
            "문서 첨부 기반 에이전트 데모 API입니다. "
            "Thread 생성, 첨부 업로드, 메시지 처리, 워크스페이스 조회, 승인 흐름을 제공합니다."
        ),
    )
    app.state.container = container

    def get_container() -> AppContainer:
        return app.state.container

    @app.get(
        "/health",
        summary="헬스 체크",
        description="서버 프로세스가 요청을 처리 가능한 상태인지 확인합니다.",
        tags=["system"],
    )
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get(
        "/model",
        summary="현재 모델 설정 조회",
        description="현재 앱이 사용하는 모델 provider와 모델명을 반환합니다.",
        tags=["system"],
    )
    def current_model(container: Annotated[AppContainer, Depends(get_container)]) -> dict[str, str]:
        return asdict(model_info(container.settings))

    @app.post(
        "/threads",
        response_model=ThreadResponse,
        summary="대화방 생성",
        description="새 thread를 생성합니다. 이후 첨부 업로드와 메시지 전송은 이 thread_id를 사용합니다.",
        tags=["threads"],
    )
    def create_thread(
        request: CreateThreadRequest,
        container: Annotated[AppContainer, Depends(get_container)],
    ) -> ThreadResponse:
        return _thread_response(container.chat_service.create_thread(request.title))

    @app.get(
        "/threads/{thread_id}/messages",
        response_model=list[MessageResponse],
        summary="대화 이력 조회",
        description="해당 thread의 user/assistant 메시지 목록을 생성 시각 순으로 반환합니다.",
        tags=["threads"],
    )
    def list_messages(thread_id: str, container: Annotated[AppContainer, Depends(get_container)]):
        try:
            return [_message_response(message) for message in container.chat_service.list_messages(thread_id)]
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post(
        "/threads/{thread_id}/messages",
        response_model=AgentMessageResponse,
        summary="에이전트 메시지 실행",
        description=(
            "사용자 메시지를 저장하고 에이전트를 실행합니다. "
            "응답 본문, 실행 계획(plan), 생성된 파일 목록, 승인 필요 정보(pending_approval)를 반환합니다."
        ),
        tags=["threads"],
    )
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
        except RuntimeError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post(
        "/threads/{thread_id}/attachments",
        response_model=AttachmentResponse,
        summary="파일 첨부 업로드",
        description=(
            "thread에 파일을 첨부합니다. 현재 샘플 MVP는 .md/.txt만 지원하며 "
            "워크스페이스 /inputs/* 경로로 등록됩니다."
        ),
        tags=["attachments"],
    )
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

    @app.get(
        "/threads/{thread_id}/workspace",
        response_model=WorkspaceFilesResponse,
        summary="워크스페이스 파일 목록 조회",
        description="해당 thread의 워크스페이스 파일 경로 목록(/inputs, /work, /research, /outputs)을 반환합니다.",
        tags=["workspace"],
    )
    def list_workspace(thread_id: str, container: Annotated[AppContainer, Depends(get_container)]):
        if container.repository.get_thread(thread_id) is None:
            raise HTTPException(status_code=404, detail=f"Thread not found: {thread_id}")
        container.attachment_service.hydrate_workspace(thread_id)
        return WorkspaceFilesResponse(files=container.workspaces.for_thread(thread_id).list_paths())

    @app.get(
        "/threads/{thread_id}/workspace/read",
        response_model=WorkspaceFileResponse,
        summary="워크스페이스 파일 내용 조회",
        description="지정한 워크스페이스 파일 경로의 텍스트 내용을 반환합니다.",
        tags=["workspace"],
    )
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

    @app.post(
        "/approvals/{approval_id}/decision",
        response_model=ApprovalDecisionResponse,
        summary="승인 요청 처리",
        description=(
            "pending 상태 승인 요청을 승인/거절 처리합니다. "
            "승인 시 mock customer reply tool이 실행되고, 중복 요청은 idempotent하게 처리됩니다."
        ),
        tags=["approvals"],
    )
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
