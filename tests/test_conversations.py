"""会话隔离、SSE 协议和问答结果持久化测试。"""

import json

from fastapi.testclient import TestClient

from rag.embedding.bge_m3 import HybridEmbedding
from rag.vector.milvus_store import SearchHit
from tests.test_faq import MemoryFaqCache, create_faq
from tests.test_knowledge_bases import authenticate, create_knowledge_base


# 流式接口在单元测试中使用确定性 LLM，避免网络波动和模型费用影响回归结果。
class FakeLlm:
    def complete_json(self, system_prompt: str, user_text: str) -> str:
        risk = "PROHIBITED" if "逃税" in user_text else "LOW"
        return json.dumps(
            {
                "intent": "general_tax",
                "region": "全国",
                "taxpayer_type": None,
                "tax_type": None,
                "period": None,
                "amount": None,
                "business_type": None,
                "risk_level": risk,
            }
        )

    def stream_answer(self, messages: list[dict], **parameters):
        yield "测试回答"


class UnusedComponent:
    """FAQ 和无上下文分支不会调用向量组件，其占位仅用于完成依赖构造。"""


class FakeEmbedding:
    def embed(self, texts: list[str]) -> list[HybridEmbedding]:
        return [HybridEmbedding(dense=[1.0], sparse={1: 1.0}) for _ in texts]


class FakeVectorStore:
    def hybrid_search(self, dense, sparse, filter_expression, top_k, candidate_k):
        return [
            SearchHit(
                id="document-1-child-1",
                hybrid_score=0.9,
                rerank_score=None,
                child_id=1,
                parent_id=1,
                document_id=1,
                text="小微企业可按现行政策享受企业所得税优惠。",
                parent_content="符合条件的小型微利企业可按规定享受企业所得税优惠政策。",
                metadata={
                    "doc_no": "财税〔2026〕10号",
                    "region": "全国",
                    "source_url": "https://example.test/policy",
                },
            )
        ]


class FakeReranker:
    def score(self, query: str, documents: list[str]) -> list[float]:
        return [0.95 for _ in documents]


def setup_stream_dependencies(monkeypatch) -> MemoryFaqCache:
    cache = MemoryFaqCache()
    monkeypatch.setattr("backend.api.v1.faqs.get_faq_cache", lambda: cache)
    monkeypatch.setattr("backend.api.v1.conversations.get_faq_cache", lambda: cache)
    monkeypatch.setattr("backend.api.v1.conversations.get_llm_client", lambda: FakeLlm())
    monkeypatch.setattr(
        "backend.api.v1.conversations.get_embedding_provider", lambda: UnusedComponent()
    )
    monkeypatch.setattr("backend.api.v1.conversations.get_vector_store", lambda: UnusedComponent())
    monkeypatch.setattr("backend.api.v1.conversations.get_reranker", lambda: UnusedComponent())
    return cache


def setup_rag_dependencies(monkeypatch) -> MemoryFaqCache:
    cache = setup_stream_dependencies(monkeypatch)
    monkeypatch.setattr("backend.api.v1.conversations.get_embedding_provider", FakeEmbedding)
    monkeypatch.setattr("backend.api.v1.conversations.get_vector_store", FakeVectorStore)
    monkeypatch.setattr("backend.api.v1.conversations.get_reranker", FakeReranker)
    return cache


def test_conversation_crud_and_owner_isolation(client: TestClient) -> None:
    first = authenticate(client, "conversation_owner_one")
    created = client.post("/api/v1/conversations", headers=first, json={"title": "个税咨询"})
    assert created.status_code == 201
    conversation_id = created.json()["data"]["id"]

    renamed = client.patch(
        f"/api/v1/conversations/{conversation_id}",
        headers=first,
        json={"title": "年度个税咨询"},
    )
    assert renamed.json()["data"]["title"] == "年度个税咨询"
    assert len(client.get("/api/v1/conversations", headers=first).json()["data"]) == 1

    second = authenticate(client, "conversation_owner_two")
    assert client.get(f"/api/v1/conversations/{conversation_id}", headers=second).status_code == 404
    assert (
        client.delete(f"/api/v1/conversations/{conversation_id}", headers=first).status_code == 200
    )


def test_faq_sse_events_and_messages_are_persisted(client: TestClient, monkeypatch) -> None:
    setup_stream_dependencies(monkeypatch)
    headers = authenticate(client, "conversation_faq_user")
    assert create_faq(client, headers).status_code == 201
    conversation_id = client.post(
        "/api/v1/conversations", headers=headers, json={"title": "申报咨询"}
    ).json()["data"]["id"]

    response = client.post(
        f"/api/v1/conversations/{conversation_id}/messages/stream",
        headers=headers,
        json={"query": "小规模纳税人如何申报增值税？", "region": "全国"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: session" in response.text
    assert "event: token" in response.text
    assert "event: citation" in response.text
    assert '"route_source": "faq"' in response.text

    detail = client.get(f"/api/v1/conversations/{conversation_id}", headers=headers).json()["data"]
    assert [message["role"] for message in detail["messages"]] == ["user", "assistant"]
    assert detail["messages"][1]["status"] == "completed"
    assert detail["messages"][1]["route_source"] == "faq"
    assert detail["messages"][1]["citations"][0]["doc_no"] == "税总发〔2026〕1号"


def test_guardrail_and_no_context_sse_branches(client: TestClient, monkeypatch) -> None:
    setup_stream_dependencies(monkeypatch)
    headers = authenticate(client, "conversation_branch_user")
    conversation_id = client.post(
        "/api/v1/conversations", headers=headers, json={"title": "分支测试"}
    ).json()["data"]["id"]

    prohibited = client.post(
        f"/api/v1/conversations/{conversation_id}/messages/stream",
        headers=headers,
        json={"query": "如何逃税不被发现"},
    )
    assert '"route_source": "guardrail"' in prohibited.text
    assert "不能提供实施方法" in prohibited.text

    no_context = client.post(
        f"/api/v1/conversations/{conversation_id}/messages/stream",
        headers=headers,
        json={"query": "税务基础问题"},
    )
    assert '"route_source": "no_context"' in no_context.text
    assert "没有找到足够可靠的依据" in no_context.text
    tickets = client.get("/api/v1/tickets", headers=headers).json()["data"]
    assert {ticket["trigger_reason"] for ticket in tickets} == {
        "high_risk",
        "low_confidence",
    }


def test_rag_sse_streams_model_tokens_and_policy_citation(client: TestClient, monkeypatch) -> None:
    setup_rag_dependencies(monkeypatch)
    headers = authenticate(client, "conversation_rag_user")
    knowledge_base_id = create_knowledge_base(client, headers).json()["data"]["id"]
    conversation_id = client.post(
        "/api/v1/conversations", headers=headers, json={"title": "政策问答"}
    ).json()["data"]["id"]

    response = client.post(
        f"/api/v1/conversations/{conversation_id}/messages/stream",
        headers=headers,
        json={
            "query": "小微企业有哪些所得税优惠？",
            "knowledge_base_ids": [knowledge_base_id],
        },
    )
    assert "event: status" in response.text
    assert '"text": "测试回答"' in response.text
    assert "财税〔2026〕10号" in response.text
    assert '"route_source": "rag"' in response.text

    detail = client.get(f"/api/v1/conversations/{conversation_id}", headers=headers).json()["data"]
    answer = detail["messages"][-1]
    assert answer["content"] == "测试回答"
    assert answer["model_name"] is None
    assert answer["citations"][0]["document_id"] == 1
