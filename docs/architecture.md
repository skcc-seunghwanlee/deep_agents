# Architecture

이 샘플은 데모 코드가 실제 프로젝트의 출발점이 될 수 있도록 adapter와 핵심 application logic을 분리합니다.

```text
main.py
  -> FastAPI app
  -> ChatService / AttachmentService / ApprovalService
  -> AgentService
  -> deep agents layer
  -> model provider, search provider, repository, storage
```

## Layer 책임

- **FastAPI adapter**: HTTP request/response 변환만 담당합니다.
- **Service layer**: thread 생성, 메시지 저장, 첨부파일 처리, agent 실행 orchestration을 담당합니다.
- **Agent layer**: deep agents 생성, prompt, subagent, tool 구성을 담당합니다.
- **Repository**: 메시지, 첨부파일, run, tool call, approval 저장을 담당합니다.
- **Storage**: 원본 첨부파일 저장소를 추상화합니다.
- **Workspace**: agent가 읽고 쓰는 `/inputs`, `/work`, `/research`, `/outputs` 파일 공간입니다.

## 실제 서비스로 확장

FastAPI 대신 Slack, Teams, WebSocket UI, batch worker를 붙이더라도 service layer는 재사용합니다.
