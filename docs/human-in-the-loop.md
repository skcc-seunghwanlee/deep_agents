# Human-in-the-loop

고객 답변 발송, 티켓 변경, DB 업데이트처럼 되돌리기 어려운 작업은 approval을 요구해야 합니다.

이 샘플은 메시지에 "발송" 또는 "send"가 포함되면 `send_customer_reply` mock tool 실행 전 approval을 생성합니다.

```text
POST /threads/{thread_id}/messages
  -> pending_approval 반환
POST /approvals/{approval_id}/decision
  -> approved=true일 때만 mock tool 실행
```

실제 서비스에서는 승인자, 승인 시각, payload hash, 실행 결과를 감사 로그로 보관하세요.
