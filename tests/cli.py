#!/usr/bin/env python3
"""FastAPI 샘플 API를 채팅 흐름처럼 호출하는 최소 데모 CLI입니다."""
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


def call(base_url: str, method: str, path: str, payload: dict | bytes | None = None, content_type: str | None = None) -> dict:
    body = payload if isinstance(payload, bytes) else json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": content_type or "application/json"} if payload is not None else {}
    url = f"{base_url.rstrip('/')}{path}"
    try:
        with urlopen(Request(url, data=body, headers=headers, method=method), timeout=15) as response:
            raw = response.read().decode("utf-8")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} {method} {url}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"FastAPI 서버에 연결할 수 없습니다. 먼저 `uvicorn main:app --reload`를 실행하세요. 원인: {exc.reason}") from exc
    return json.loads(raw) if raw else {}


def multipart(path: Path, boundary: str) -> bytes:
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


def attach(base_url: str, thread_id: str, file_path: Path) -> dict:
    boundary = f"----deep-agents-cli-{uuid.uuid4().hex}"
    return call(
        base_url,
        "POST",
        f"/threads/{thread_id}/attachments",
        multipart(file_path, boundary),
        f"multipart/form-data; boundary={boundary}",
    )


def run(args: argparse.Namespace) -> None:
    base_url = args.base_url.rstrip("/")
    print("=== Deep Agents FastAPI CLI 데모 ===")
    print(f"api> {base_url}")

    thread_id = call(base_url, "POST", "/threads", {"title": args.title})["id"]
    print(f"system> thread created: {thread_id}")

    if args.file:
        print(f"user> /attach {args.file}")
        uploaded = attach(base_url, thread_id, Path(args.file))
        print(f"assistant> 파일을 첨부했습니다. Agent path: {uploaded['agent_file_path']}")

    pending_approval = None
    for message in args.message:
        print(f"\nuser> {message}")
        response = call(base_url, "POST", f"/threads/{thread_id}/messages", {"content": message})
        print("assistant>")
        print(response["message"]["content"])
        pending_approval = response.get("pending_approval") or pending_approval

    files = call(base_url, "GET", f"/threads/{thread_id}/workspace").get("files", [])
    print("\n/files")
    print("\n".join(f"- {path}" for path in files))

    if args.read:
        result = call(base_url, "GET", f"/threads/{thread_id}/workspace/read?{urlencode({'path': args.read})}")
        print(f"\n/read {args.read}\n{result.get('content', '')}")

    if args.approve and pending_approval:
        for label in ["승인", "승인 다시 누름"]:
            print(f"\nuser> {label}")
            result = call(base_url, "POST", f"/approvals/{pending_approval['id']}/decision", {"approved": True})
            print(f"assistant> {result['result']}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="FastAPI 샘플 API를 채팅처럼 호출합니다.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--title", default="cli demo")
    parser.add_argument("--file", default="examples/data/sample_policy.md")
    parser.add_argument("--message", action="append", default=[])
    parser.add_argument("--read", default="/outputs/summary.md")
    parser.add_argument("--approve", action="store_true")
    args = parser.parse_args(argv)
    args.message = args.message or ["이 문서 요약하고 리스크 찾아줘", "최근 기준도 검색해서 고객 답변 초안 만들어줘", "이거 발송해줘"]
    return args


if __name__ == "__main__":
    try:
        run(parse_args(sys.argv[1:]))
    except RuntimeError as exc:
        print(f"error> {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
