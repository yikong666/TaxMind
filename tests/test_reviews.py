"""回答反馈、人工转交、工单隔离与状态机测试。"""

from fastapi.testclient import TestClient

from tests.test_conversations import setup_stream_dependencies
from tests.test_faq import create_faq
from tests.test_knowledge_bases import authenticate


# 使用 FAQ 确定性回答创建一条可反馈的已完成 AI 消息。
def create_answer(client: TestClient, headers: dict[str, str]) -> int:
    assert create_faq(client, headers).status_code == 201
    conversation_id = client.post(
        "/api/v1/conversations", headers=headers, json={"title": "反馈测试"}
    ).json()["data"]["id"]
    response = client.post(
        f"/api/v1/conversations/{conversation_id}/messages/stream",
        headers=headers,
        json={"query": "小规模纳税人如何申报增值税？"},
    )
    assert response.status_code == 200
    messages = client.get(f"/api/v1/conversations/{conversation_id}", headers=headers).json()[
        "data"
    ]["messages"]
    return messages[-1]["id"]


def test_feedback_requires_reason_and_rejects_duplicate(client: TestClient, monkeypatch) -> None:
    setup_stream_dependencies(monkeypatch)
    headers = authenticate(client, "review_feedback_user")
    message_id = create_answer(client, headers)

    missing_reason = client.post(
        f"/api/v1/messages/{message_id}/feedback",
        headers=headers,
        json={"feedback_type": "dislike"},
    )
    assert missing_reason.status_code == 422

    created = client.post(
        f"/api/v1/messages/{message_id}/feedback",
        headers=headers,
        json={"feedback_type": "dislike", "reason": "操作步骤不够详细"},
    )
    assert created.status_code == 201
    assert created.json()["data"]["reason"] == "操作步骤不够详细"
    duplicate = client.post(
        f"/api/v1/messages/{message_id}/feedback",
        headers=headers,
        json={"feedback_type": "like"},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "FEEDBACK_EXISTS"


def test_handoff_ticket_status_flow_and_owner_isolation(client: TestClient, monkeypatch) -> None:
    setup_stream_dependencies(monkeypatch)
    first = authenticate(client, "review_ticket_owner_one")
    message_id = create_answer(client, first)
    created = client.post(
        f"/api/v1/messages/{message_id}/handoff",
        headers=first,
        json={"reason": "希望税务人员复核"},
    )
    assert created.status_code == 201
    ticket = created.json()["data"]
    ticket_id = ticket["id"]
    assert ticket["status"] == "pending"
    assert ticket["user_feedback"] == "希望税务人员复核"
    assert ticket["user_question"] == "小规模纳税人如何申报增值税？"

    invalid = client.patch(
        f"/api/v1/tickets/{ticket_id}",
        headers=first,
        json={"status": "resolved", "resolution": "已复核"},
    )
    assert invalid.status_code == 400
    assert invalid.json()["code"] == "INVALID_TICKET_TRANSITION"
    processing = client.patch(
        f"/api/v1/tickets/{ticket_id}", headers=first, json={"status": "processing"}
    )
    assert processing.json()["data"]["status"] == "processing"
    no_resolution = client.patch(
        f"/api/v1/tickets/{ticket_id}", headers=first, json={"status": "resolved"}
    )
    assert no_resolution.json()["code"] == "TICKET_RESOLUTION_REQUIRED"
    resolved = client.patch(
        f"/api/v1/tickets/{ticket_id}",
        headers=first,
        json={"status": "resolved", "resolution": "政策依据与回答一致"},
    )
    assert resolved.json()["data"]["resolution"] == "政策依据与回答一致"

    second = authenticate(client, "review_ticket_owner_two")
    assert client.get(f"/api/v1/tickets/{ticket_id}", headers=second).status_code == 404
    assert (
        client.post(
            f"/api/v1/messages/{message_id}/feedback",
            headers=second,
            json={"feedback_type": "like"},
        ).status_code
        == 404
    )


def test_duplicate_handoff_is_rejected(client: TestClient, monkeypatch) -> None:
    setup_stream_dependencies(monkeypatch)
    headers = authenticate(client, "review_duplicate_handoff")
    message_id = create_answer(client, headers)
    endpoint = f"/api/v1/messages/{message_id}/handoff"
    assert client.post(endpoint, headers=headers, json={}).status_code == 201
    duplicate = client.post(endpoint, headers=headers, json={})
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "TICKET_EXISTS"
