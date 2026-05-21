# Deep Agents FastAPI 샘플

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

## 로컬 실행 체크

`http://127.0.0.1:8000/docs` 접속 시 `/openapi.json`에서 500 오류가 나면 `.env` 값 문제가 아니라 FastAPI dependency annotation 처리 문제일 수 있습니다. 최신 코드를 받은 뒤 아래처럼 확인하세요.

```bash
python - <<'PY'
from sample_agents.app import app
print(app.openapi()["info"])
PY
```

기본 fake provider는 OpenAI API key 없이 실행됩니다. 실제 OpenAI/Ollama provider를 사용할 때만 위 환경변수를 채우면 됩니다.

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

## HTTP CLI 데모

FastAPI 서버를 띄운 뒤 `tests/cli.py`로 같은 API 계약을 터미널 채팅 형태로 가볍게 호출할 수 있습니다. 이 파일은 테스트용 보조 스크립트라서 의도적으로 최소 구현만 담았습니다.

```bash
uvicorn main:app --reload
python tests/cli.py --approve
```

이 CLI는 별도 SDK 없이 표준 라이브러리 `urllib`만 사용해 `/threads`, `/attachments`, `/messages`, `/workspace`, `/approvals` endpoint를 호출합니다.


## CLI로 실제 대화 데모하기

FastAPI 서버가 이미 켜져 있다면 아래 명령으로 바로 대화형 데모를 실행할 수 있습니다.

```bash
python tests/cli.py --approve
```

기본 동작:
- thread 생성
- `examples/data/sample_policy.md` 파일 첨부
- 3개 메시지 순차 실행
- `/files`, `/read /outputs/summary.md` 출력
- 승인 2회 호출(중복 승인 idempotency 확인)

### 파일 첨부 경로 바꿔서 실행

```bash
python tests/cli.py --file /절대/경로/your_policy.md --approve
```

지원 첨부 형식은 `.md`, `.txt`입니다.

### 메시지 직접 지정

```bash
python tests/cli.py \
  --message "이 문서 핵심만 요약해줘" \
  --message "리스크 3개만 뽑아줘" \
  --message "고객 답변 초안 만들고 발송 준비해줘" \
  --approve
```

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
