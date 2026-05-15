# Production Checklist

- 인증/인가와 tenant isolation 추가
- API rate limit과 model/tool call budget 설정
- PII detection/redaction middleware 추가
- PostgreSQL 같은 운영 DB로 repository 교체
- S3/GCS 같은 object storage로 첨부파일 저장소 교체
- PDF/DOCX/OCR parser tool 추가
- 실제 RAG/search provider 연결
- LangSmith/OpenTelemetry 등 tracing 추가
- approval payload hash와 감사 로그 보강
