# Extension Guide

## FastAPI에서 Web UI로

현재 API를 그대로 호출하는 React/Vue/Svelte UI를 얇게 붙이면 됩니다. Agent core는 변경하지 않습니다.

## Slack/Teams Bot으로

메신저 event handler는 adapter로만 동작하고 `ChatService`, `AttachmentService`, `ApprovalService`를 호출합니다.

## PostgreSQL로 교체

`ConversationRepository` protocol을 구현하는 `PostgresConversationRepository`를 추가하고 app wiring만 교체합니다.

## S3/GCS로 교체

`FileStorage` protocol을 구현하는 object storage backend를 추가하고 `message_attachments.storage_uri`에 `s3://...` 또는 `gs://...`를 저장합니다.
