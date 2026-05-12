import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from sample_agents.app import create_app
from sample_agents.config import Settings


def test_fastapi_document_review_flow(tmp_path):
    app = create_app(
        Settings(
            model_provider="fake",
            model_name="fake",
            database_url="memory",
            local_storage_dir=tmp_path,
        )
    )
    client = TestClient(app)

    created = client.post("/threads", json={"title": "demo"})
    assert created.status_code == 200
    thread_id = created.json()["id"]

    uploaded = client.post(
        f"/threads/{thread_id}/attachments",
        files={"file": ("policy.md", "# Policy\n 개인정보 보관 기간과 제3자 제공 안내".encode(), "text/markdown")},
    )
    assert uploaded.status_code == 200
    assert uploaded.json()["agent_file_path"] == "/inputs/policy.md"

    reply = client.post(
        f"/threads/{thread_id}/messages",
        json={"content": "검색해서 리스크 찾고 고객 답변 발송 준비해줘"},
    )
    assert reply.status_code == 200
    body = reply.json()
    assert "/research/search_results.md" in body["generated_files"]
    assert body["pending_approval"]["requested_action"] == "send_customer_reply"

    workspace = client.get(f"/threads/{thread_id}/workspace")
    assert workspace.status_code == 200
    assert "/outputs/customer_reply.md" in workspace.json()["files"]

    approval_id = body["pending_approval"]["id"]
    decision = client.post(f"/approvals/{approval_id}/decision", json={"approved": True})
    assert decision.status_code == 200
    assert "Mock send completed" in decision.json()["result"]
