# Database Schema

MVP는 SQLite를 사용하지만 `persistence/repositories.py`의 interface 뒤에 PostgreSQL, MySQL, DynamoDB 등을 붙일 수 있습니다.

주요 테이블은 `src/sample_agents/persistence/schema.sql`에 정의되어 있습니다.

- `agent_threads`: 앱 대화 thread
- `messages`: user/assistant/tool/system 메시지
- `message_attachments`: 원본 파일 metadata와 agent workspace path 매핑
- `agent_runs`: agent 실행 단위
- `tool_calls`: 검색, 발송 등 tool 호출 이력
- `approvals`: human-in-the-loop 승인 요청과 결정

Deep agents checkpointer는 runtime state 저장에 가깝고, 위 DB는 서비스 관점의 감사/조회/분석 데이터를 저장합니다.
