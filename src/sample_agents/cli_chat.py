"""FastAPI 서버와 대화형으로 상호작용하는 터미널 채팅 데모 CLI."""

from __future__ import annotations

import argparse
import json
import mimetypes
import sys
import uuid
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class CliError(RuntimeError):
    """사용자에게 표시할 수 있는 CLI 실행 오류."""


def _call(base_url: str, method: str, path: str, payload: dict | bytes | None = None, content_type: str | None = None) -> dict:
    body = payload if isinstance(payload, bytes) else json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": content_type or "application/json"} if payload is not None else {}
    url = f"{base_url.rstrip('/')}{path}"
    try:
        with urlopen(Request(url, data=body, headers=headers, method=method), timeout=20) as response:
            raw = response.read().decode("utf-8")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise CliError(f"HTTP {exc.code} {method} {url}: {detail}") from exc
    except URLError as exc:
        raise CliError(
            "FastAPI 서버 연결에 실패했습니다. 먼저 `uvicorn main:app --reload`를 실행했는지 확인하세요. "
            f"원인: {exc.reason}"
        ) from exc
    return json.loads(raw) if raw else {}


def _multipart(path: Path, boundary: str) -> bytes:
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return b"".join(
        [
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="file"; filename="{path.name}"\r\n'.encode(),
            f"Content-Type: {mime}\r\n\r\n".encode(),
            path.read_bytes(),
            b"\r\n",
            f"--{boundary}--\r\n".encode(),
        ]
    )


def _upload(base_url: str, thread_id: str, file_path: Path) -> dict:
    boundary = f"----deep-agents-chat-{uuid.uuid4().hex}"
    return _call(
        base_url,
        "POST",
        f"/threads/{thread_id}/attachments",
        _multipart(file_path, boundary),
        f"multipart/form-data; boundary={boundary}",
    )


def _print_help() -> None:
    print(
        """\n사용 가능한 명령어:
  /help                    도움말 출력
  /attach <파일경로>       .md/.txt 파일 첨부
  /files                   워크스페이스 파일 목록 출력
  /read <워크스페이스경로> 파일 내용 출력
  /approve <approval_id>   승인 실행
  /model                   현재 모델 설정 조회
  /exit                    종료
\n일반 텍스트를 입력하면 에이전트에게 메시지를 전송합니다.
"""
    )


def run(args: argparse.Namespace) -> int:
    base_url = args.base_url.rstrip("/")
    thread = _call(base_url, "POST", "/threads", {"title": args.title})
    thread_id = thread["id"]

    print("=== Deep Agents 대화형 데모 ===")
    print(f"api> {base_url}")
    print(f"thread> {thread_id}")

    model = _call(base_url, "GET", "/model")
    print(f"model> {model.get('provider')}:{model.get('name')}")
    _print_help()

    last_pending_approval_id: str | None = None

    while True:
        try:
            raw = input("you> ").strip()
        except EOFError:
            print("\nassistant> 입력이 종료되어 채팅을 마칩니다.")
            return 0

        if not raw:
            continue
        if raw in {"/exit", "exit", "quit"}:
            print("assistant> 채팅을 종료합니다.")
            return 0
        if raw == "/help":
            _print_help()
            continue

        if raw.startswith("/attach "):
            file_path = Path(raw.split(" ", 1)[1]).expanduser()
            if not file_path.exists():
                print(f"assistant> 파일을 찾을 수 없습니다: {file_path}")
                continue
            uploaded = _upload(base_url, thread_id, file_path)
            print(f"assistant> 첨부 완료: {uploaded['original_filename']} -> {uploaded['agent_file_path']}")
            continue

        if raw == "/files":
            files = _call(base_url, "GET", f"/threads/{thread_id}/workspace").get("files", [])
            print("assistant> workspace files")
            for path in files:
                print(f"  - {path}")
            continue

        if raw.startswith("/read "):
            path = raw.split(" ", 1)[1]
            query = urlencode({"path": path})
            response = _call(base_url, "GET", f"/threads/{thread_id}/workspace/read?{query}")
            print(f"assistant> {response.get('path')}")
            print(response.get("content", ""))
            continue

        if raw.startswith("/approve "):
            approval_id = raw.split(" ", 1)[1].strip()
            response = _call(base_url, "POST", f"/approvals/{approval_id}/decision", {"approved": True})
            print(f"assistant> {response.get('result')}")
            continue

        if raw == "/model":
            model = _call(base_url, "GET", "/model")
            print(f"assistant> provider={model.get('provider')} model={model.get('name')}")
            continue

        response = _call(base_url, "POST", f"/threads/{thread_id}/messages", {"content": raw})
        message = response.get("message", {})
        print("assistant>")
        print(message.get("content", ""))

        plan = response.get("plan") or []
        if plan:
            print("\n[plan]")
            for step in plan:
                print(f"- {step}")

        files = response.get("generated_files") or []
        if files:
            print("\n[generated_files]")
            for path in files:
                print(f"- {path}")

        pending = response.get("pending_approval")
        if pending:
            last_pending_approval_id = pending.get("id")
            print(
                "\n[approval_required] "
                f"id={pending.get('id')} action={pending.get('requested_action')}"
            )
            print("승인하려면 /approve <approval_id> 를 입력하세요.")
        elif last_pending_approval_id:
            print(f"\n[last_approval] {last_pending_approval_id}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="FastAPI 기반 Deep Agents 대화형 데모 CLI")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--title", default="interactive demo")
    return parser.parse_args(argv)


if __name__ == "__main__":
    try:
        raise SystemExit(run(parse_args(sys.argv[1:])))
    except CliError as exc:
        print(f"error> {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
