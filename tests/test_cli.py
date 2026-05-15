from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from cli import main


class DemoHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    workspace_files = [
        "/inputs/sample_policy.md",
        "/outputs/summary.md",
        "/outputs/risks.md",
        "/outputs/customer_reply.md",
    ]
    approval_count = 0

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        self.rfile.read(length)
        if self.path == "/threads":
            self._send({"id": "thread_demo", "title": "cli demo", "created_at": "2026-05-15T00:00:00Z"})
        elif self.path == "/threads/thread_demo/attachments":
            self._send(
                {
                    "id": "att_demo",
                    "original_filename": "sample_policy.md",
                    "agent_file_path": "/inputs/sample_policy.md",
                    "size_bytes": 12,
                }
            )
        elif self.path == "/threads/thread_demo/messages":
            self._send(
                {
                    "message": {
                        "id": "msg_demo",
                        "role": "assistant",
                        "content": "작업 계획에 따라 문서를 검토했습니다.\n\n생성된 파일:\n- /outputs/summary.md",
                        "created_at": "2026-05-15T00:00:00Z",
                    },
                    "plan": ["첨부 문서 확인"],
                    "generated_files": ["/outputs/summary.md"],
                    "pending_approval": {
                        "id": "approval_demo",
                        "requested_action": "send_customer_reply",
                    },
                }
            )
        elif self.path == "/approvals/approval_demo/decision":
            DemoHandler.approval_count += 1
            result = (
                "Mock send completed. Preview length=10"
                if DemoHandler.approval_count == 1
                else "이미 처리된 승인 요청입니다. status=approved"
            )
            self._send({"result": result})
        else:
            self.send_error(404)

    def do_GET(self):
        if self.path == "/threads/thread_demo/workspace":
            self._send({"files": self.workspace_files})
        elif self.path.startswith("/threads/thread_demo/workspace/read"):
            self._send({"path": "/outputs/summary.md", "content": "# Summary\n\n- sample"})
        else:
            self.send_error(404)

    def log_message(self, *args):
        return

    def _send(self, payload):
        body = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def test_cli_calls_fastapi_contract(tmp_path, capsys):
    sample = tmp_path / "sample_policy.md"
    sample.write_text("# sample", encoding="utf-8")
    server = ThreadingHTTPServer(("127.0.0.1", 0), DemoHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        code = main(
            [
                "--base-url",
                f"http://127.0.0.1:{server.server_address[1]}",
                "--file",
                str(sample),
                "--message",
                "이 문서 요약해줘",
                "--approve",
            ]
        )
    finally:
        server.shutdown()
        server.server_close()

    output = capsys.readouterr().out
    assert code == 0
    assert "system> thread created: thread_demo" in output
    assert "assistant> 파일을 첨부했습니다. Agent path: /inputs/sample_policy.md" in output
    assert "Mock send completed" in output
    assert "이미 처리된 승인 요청" in output
