# Deep Agents FastAPI Sample

실제 프로젝트로 확장하기 쉬운 **FastAPI 기반 deep agents 샘플**입니다. 데모는 문서 검토(Document Review) 시나리오를 사용하지만, 내부 구조는 API adapter, service layer, repository, storage, model/search provider를 분리해 FastAPI, Slack bot, batch worker, Web UI로 확장할 수 있게 만들었습니다.

## 핵심 컨셉

사용자는 API로 thread를 만들고, `.md`/`.txt` 파일을 첨부한 뒤 메시지를 보냅니다. Agent는 workspace의 `/inputs` 문서를 읽고 `/work`, `/research`, `/outputs`에 작업 산출물을 남깁니다.

```text
FastAPI Adapter
  -> Application Services
  -> Agent Service
  -> deep agents / model provider / tools
  -> Repository + Storage + Workspace
```

## 빠른 실행

기본값은 `MODEL_PROVIDER=fake`라서 OpenAI API key 없이도 API, 파일첨부, workspace, approval 흐름을 확인할 수 있습니다.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
uvicorn main:app --reload
```

OpenAI 모델로 실제 LLM 동작을 확인하려면 `.env` 또는 환경변수를 설정합니다.

```bash
export MODEL_PROVIDER=openai
export MODEL_NAME=gpt-4.1-mini
export OPENAI_API_KEY=sk-...
uvicorn main:app --reload
```

로컬 Ollama를 쓰고 싶다면 다음처럼 확장할 수 있습니다.

```bash
export MODEL_PROVIDER=ollama
export MODEL_NAME=qwen2.5:7b
export OLLAMA_BASE_URL=http://localhost:11434
```

## API 사용 예시

### 1. Thread 생성

```bash
curl -s -X POST http://127.0.0.1:8000/threads \
  -H 'Content-Type: application/json' \
  -d '{"title":"policy review"}'
```

### 2. 파일 첨부

```bash
curl -s -X POST http://127.0.0.1:8000/threads/{thread_id}/attachments \
  -F file=@examples/data/sample_policy.md
```

### 3. 메시지 전송

```bash
curl -s -X POST http://127.0.0.1:8000/threads/{thread_id}/messages \
  -H 'Content-Type: application/json' \
  -d '{"content":"이 문서를 요약하고 리스크와 고객 답변 초안을 만들어줘"}'
```

### 4. Workspace 확인

```bash
curl -s http://127.0.0.1:8000/threads/{thread_id}/workspace
curl -s 'http://127.0.0.1:8000/threads/{thread_id}/workspace/read?path=/outputs/summary.md'
```

### 5. Approval 결정

메시지에 "발송"이 포함되면 mock customer reply 발송 전 approval이 생성됩니다.

```bash
curl -s -X POST http://127.0.0.1:8000/approvals/{approval_id}/decision \
  -H 'Content-Type: application/json' \
  -d '{"approved":true}'
```

## HTTP CLI demo

FastAPI 서버를 띄운 뒤 `tests/cli.py`로 같은 API contract를 터미널 채팅 형태로 호출할 수 있습니다.

```bash
uvicorn main:app --reload
python tests/cli.py --approve
```

이 CLI는 별도 SDK 없이 표준 라이브러리 `urllib`로 `/threads`, `/attachments`, `/messages`, `/workspace`, `/approvals` endpoint를 호출합니다.

## 실제 프로젝트 확장 포인트

- `sample_agents.app`: FastAPI adapter와 dependency wiring
- `services/`: API, bot, batch worker가 재사용할 application service layer
- `agents/factory.py`: deep agents 생성 책임 중앙화
- `integrations/models.py`: OpenAI/Ollama/Fake model provider 교체 지점
- `integrations/search_providers.py`: Mock/Web/RAG/MCP 검색 provider 교체 지점
- `persistence/`: SQLite/in-memory repository와 DB schema
- `storage/`: local/S3/GCS 등 첨부파일 저장소 교체 지점

## MVP에서 의도적으로 단순화한 것

- 첨부파일은 `.md`, `.txt`만 지원합니다.
- PDF/DOCX/OCR 파싱은 별도 parser 또는 MCP/API tool로 확장합니다.
- 검색은 `MockSearchProvider`가 기본입니다.
- 실제 이메일 발송 대신 `send_customer_reply` mock tool을 사용합니다.
- fake model은 API 구조 확인용이며, 실제 agent 품질 확인은 OpenAI/Ollama provider로 전환해야 합니다.
