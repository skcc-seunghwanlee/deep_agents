#!/usr/bin/env python3
"""Small HTTP CLI for exercising the FastAPI sample app.

Run the API first:
    uvicorn main:app --reload

Then run:
    python tests/cli.py --file examples/data/sample_policy.md \
      --message "이 문서를 요약하고 리스크 찾아줘" \
      --message "최근 기준도 검색해서 고객 답변 초안 만들어줘" \
      --message "이거 발송해줘" --approve
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import sys
import uuid
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class ApiError(RuntimeError):
    pass


class FastApiChatClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def create_thread(self, title: str) -> dict[str, Any]:
        return self._json("POST", "/threads", {"title": title})

    def upload_attachment(self, thread_id: str, file_path: Path) -> dict[str, Any]:
        boundary = f"----deep-agents-cli-{uuid.uuid4().hex}"
        content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        body = self._multipart_file_body(boundary, "file", file_path, content_type)
        return self._request_json(
            "POST",
            f"/threads/{thread_id}/attachments",
            body,
            {"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )

    def send_message(self, thread_id: str, content: str) -> dict[str, Any]:
        return self._json("POST", f"/threads/{thread_id}/messages", {"content": content})

    def list_workspace(self, thread_id: str) -> dict[str, Any]:
        return self._json("GET", f"/threads/{thread_id}/workspace")

    def read_workspace_file(self, thread_id: str, path: str) -> dict[str, Any]:
        return self._json("GET", f"/threads/{thread_id}/workspace/read?{urlencode({'path': path})}")

    def decide_approval(self, approval_id: str, approved: bool) -> dict[str, Any]:
        return self._json("POST", f"/approvals/{approval_id}/decision", {"approved": approved})

    def _json(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        headers = {} if payload is None else {"Content-Type": "application/json"}
        return self._request_json(method, path, body, headers)

    def _request_json(
        self,
        method: str,
        path: str,
        body: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        url = f"{self.base_url}{path if path.startswith('/') else '/' + path}"
        request = Request(url, data=body, headers=headers or {}, method=method)
        try:
            with urlopen(request, timeout=15) as response:
                raw = response.read().decode("utf-8")
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise ApiError(f"HTTP {exc.code} {method} {url}: {detail}") from exc
        except URLError as exc:
            raise ApiError(
                f"Cannot reach FastAPI server at {self.base_url}. "
                "Start it with `uvicorn main:app --reload` first. "
                f"Original error: {exc.reason}"
            ) from exc
        return json.loads(raw) if raw else {}

    def _multipart_file_body(self, boundary: str, field_name: str, file_path: Path, content_type: str) -> bytes:
        filename = file_path.name
        file_content = file_path.read_bytes()
        lines = [
            f"--{boundary}\r\n".encode(),
            (
                f'Content-Disposition: form-data; name="{field_name}"; '
                f'filename="{filename}"\r\n'
            ).encode(),
            f"Content-Type: {content_type}\r\n\r\n".encode(),
            file_content,
            b"\r\n",
            f"--{boundary}--\r\n".encode(),
        ]
        return b"".join(lines)


def run_demo(args: argparse.Namespace) -> None:
    client = FastApiChatClient(args.base_url)
    print("=== Deep Agents FastAPI CLI demo ===")
    print(f"api> {args.base_url}")

    thread = client.create_thread(args.title)
    thread_id = thread["id"]
    print(f"system> thread created: {thread_id}")

    if args.file:
        file_path = Path(args.file)
        print(f"user> /attach {file_path}")
        attachment = client.upload_attachment(thread_id, file_path)
        print(f"assistant> 파일을 첨부했습니다. Agent path: {attachment['agent_file_path']}")

    pending_approval: dict[str, Any] | None = None
    for message in args.message:
        print(f"\nuser> {message}")
        response = client.send_message(thread_id, message)
        print("assistant>")
        print(response["message"]["content"])
        pending_approval = response.get("pending_approval") or pending_approval

    workspace = client.list_workspace(thread_id)
    print("\n/files")
    for path in workspace.get("files", []):
        print(f"- {path}")

    if args.read:
        print(f"\n/read {args.read}")
        content = client.read_workspace_file(thread_id, args.read)
        print(content.get("content", ""))

    if args.approve and pending_approval:
        approval_id = pending_approval["id"]
        print("\nuser> 승인")
        decision = client.decide_approval(approval_id, True)
        print(f"assistant> {decision['result']}")
        print("\nuser> 승인 다시 누름")
        duplicate = client.decide_approval(approval_id, True)
        print(f"assistant> {duplicate['result']}")
    elif args.approve:
        print("\napproval> pending approval이 없습니다.")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Exercise the Deep Agents FastAPI sample over HTTP.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="FastAPI server base URL")
    parser.add_argument("--title", default="cli demo", help="Thread title")
    parser.add_argument("--file", default="examples/data/sample_policy.md", help="Markdown/TXT file to upload")
    parser.add_argument(
        "--message",
        action="append",
        default=[],
        help="Message to send. Can be repeated. Defaults to a 3-turn document review demo.",
    )
    parser.add_argument("--read", default="/outputs/summary.md", help="Workspace path to read after messages")
    parser.add_argument("--approve", action="store_true", help="Approve and retry any pending approval")
    args = parser.parse_args(argv)
    if not args.message:
        args.message = [
            "이 문서 요약하고 리스크 찾아줘",
            "최근 기준도 검색해서 고객 답변 초안 만들어줘",
            "이거 발송해줘",
        ]
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        run_demo(args)
    except ApiError as exc:
        print(f"error> {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
