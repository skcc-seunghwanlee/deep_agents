# File Processing

MVP는 `.md`, `.txt` 첨부만 지원합니다.

```text
HTTP Upload
  -> LocalFileStorage에 원본 저장
  -> message_attachments metadata 저장
  -> AgentWorkspace /inputs/{filename}에 텍스트 등록
  -> agent가 /inputs 파일을 읽고 /outputs 산출물 작성
```

PDF, DOCX, XLSX, 이미지 OCR은 deep agents filesystem 자체 기능이라기보다 별도 parser/tool의 책임입니다. 실제 프로젝트에서는 parser 결과를 Markdown으로 변환해 workspace에 등록하는 방식을 권장합니다.
