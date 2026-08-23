from datetime import date

import pytest
from fastapi.testclient import TestClient

from backend.core.exceptions import BusinessError
from backend.services.retrieval import RetrievalService
from rag.embedding.bge_m3 import HybridEmbedding
from rag.retrieval.filters import build_metadata_filter
from rag.vector.milvus_store import SearchHit
from tests.test_knowledge_bases import authenticate, create_knowledge_base


class FakeEmbedding:
    def embed(self, texts: list[str]) -> list[HybridEmbedding]:
        return [HybridEmbedding([1.0, 0.0], {9: 0.7}) for _ in texts]


class FakeReranker:
    def score(self, query: str, passages: list[str]) -> list[float]:
        # 后出现的候选分数更高，用于验证服务确实采用重排序结果。
        return [float(index) for index, _ in enumerate(passages)]


class SearchStore:
    def __init__(self) -> None:
        self.expression = ""

    def hybrid_search(self, dense, sparse, expression, top_k, candidate_k):
        self.expression = expression
        return [
            SearchHit(
                id="doc-1-child-1",
                hybrid_score=0.91,
                rerank_score=None,
                child_id=1,
                parent_id=1,
                document_id=1,
                text="小规模纳税人适用增值税优惠。",
                parent_content="增值税优惠政策完整内容。",
                metadata={
                    "region": "全国",
                    "doc_no": "财税〔2026〕1号",
                    "tax_type": "增值税",
                    "taxpayer_type": "小规模纳税人",
                    "effective_start": 20260101,
                    "effective_end": 20261231,
                    "policy_status": "active",
                    "source_url": "https://www.chinatax.gov.cn/example",
                },
            )
        ]


class CandidateStore:
    def hybrid_search(self, dense, sparse, expression, top_k, candidate_k):
        return [
            SearchHit(
                id=f"hit-{index}",
                hybrid_score=0.9 - index / 10,
                rerank_score=None,
                child_id=index,
                parent_id=parent_id,
                document_id=1,
                text=f"候选 {index}",
                parent_content=f"父块 {parent_id}",
                metadata={"policy_status": "active"},
            )
            for index, parent_id in [(1, 10), (2, 10), (3, 20)]
        ]


class EmptyStore:
    def hybrid_search(self, dense, sparse, expression, top_k, candidate_k):
        return []


class FixedReranker:
    def score(self, query: str, passages: list[str]) -> list[float]:
        return [0.2, 0.9, 0.8]


class FailingReranker:
    def score(self, query: str, passages: list[str]) -> list[float]:
        raise RuntimeError("model failed")


class OwnedRepository:
    def get(self, knowledge_base_id: int, owner_id: int):
        return object()


def test_current_policy_filter_excludes_expired_and_replaced() -> None:
    expression = build_metadata_filter(
        owner_id=7,
        knowledge_base_ids=[3, 2, 3],
        query_date=date(2026, 8, 23),
        region="重庆",
    )
    assert "owner_id == 7" in expression
    assert "knowledge_base_id in [2, 3]" in expression
    assert 'policy_status == "active"' in expression
    assert 'region in ["全国", "重庆"]' in expression
    assert "effective_start <= 20260823" in expression
    assert "effective_end == 0 or effective_end >= 20260823" in expression
    assert 'policy_status == "expired"' not in expression
    assert 'policy_status == "replaced"' not in expression


def test_national_query_does_not_mix_local_policy() -> None:
    expression = build_metadata_filter(
        owner_id=1,
        knowledge_base_ids=[1],
        query_date=date(2026, 1, 1),
        region="全国",
    )
    assert 'region in ["全国"]' in expression
    assert "重庆" not in expression


def test_optional_taxpayer_filters_are_escaped() -> None:
    expression = build_metadata_filter(
        owner_id=1,
        knowledge_base_ids=[1],
        query_date=date(2026, 1, 1),
        region="重庆",
        tax_type='增值税"测试',
        taxpayer_type="小规模纳税人",
    )
    assert 'tax_type == "增值税\\"测试"' in expression
    assert 'taxpayer_type == "小规模纳税人"' in expression


def test_empty_knowledge_base_filter_is_rejected() -> None:
    with pytest.raises(ValueError, match="至少选择一个知识库"):
        build_metadata_filter(
            owner_id=1,
            knowledge_base_ids=[],
            query_date=date.today(),
            region="全国",
        )


def test_hybrid_retrieval_returns_parent_context_and_citation(
    client: TestClient, monkeypatch
) -> None:
    headers = authenticate(client)
    knowledge_base_id = create_knowledge_base(client, headers).json()["data"]["id"]
    store = SearchStore()
    monkeypatch.setattr("backend.api.v1.retrieval.get_embedding_provider", lambda: FakeEmbedding())
    monkeypatch.setattr("backend.api.v1.retrieval.get_vector_store", lambda: store)
    monkeypatch.setattr("backend.api.v1.retrieval.get_reranker", lambda: FakeReranker())

    response = client.post(
        "/api/v1/retrieval/search",
        headers=headers,
        json={
            "query": "重庆小规模纳税人有什么增值税优惠？",
            "knowledge_base_ids": [knowledge_base_id],
            "region": "重庆",
            "query_date": "2026-08-23",
            "tax_type": "增值税",
            "top_k": 5,
        },
    )

    assert response.status_code == 200
    hit = response.json()["data"][0]
    assert hit["parent_content"] == "增值税优惠政策完整内容。"
    assert hit["doc_no"] == "财税〔2026〕1号"
    assert hit["hybrid_score"] == 0.91
    assert hit["rerank_score"] == 0.0
    assert "effective_start <= 20260823" in store.expression
    assert f"knowledge_base_id in [{knowledge_base_id}]" in store.expression


def test_retrieval_rejects_unowned_knowledge_base(client: TestClient, monkeypatch) -> None:
    headers = authenticate(client)
    monkeypatch.setattr("backend.api.v1.retrieval.get_embedding_provider", lambda: FakeEmbedding())
    monkeypatch.setattr("backend.api.v1.retrieval.get_vector_store", lambda: SearchStore())
    monkeypatch.setattr("backend.api.v1.retrieval.get_reranker", lambda: FakeReranker())

    response = client.post(
        "/api/v1/retrieval/search",
        headers=headers,
        json={"query": "测试", "knowledge_base_ids": [999], "region": "全国"},
    )
    assert response.status_code == 404
    assert response.json()["code"] == "KNOWLEDGE_BASE_NOT_FOUND"


def test_reranker_sorts_and_deduplicates_parent_context() -> None:
    service = RetrievalService(
        OwnedRepository(), FakeEmbedding(), CandidateStore(), FixedReranker(), candidate_k=20
    )
    hits = service.search(
        owner_id=1,
        query="增值税优惠",
        knowledge_base_ids=[1],
        region="全国",
        query_date=date(2026, 8, 23),
        tax_type=None,
        taxpayer_type=None,
        top_k=2,
    )
    assert [hit.id for hit in hits] == ["hit-2", "hit-3"]
    assert [hit.rerank_score for hit in hits] == [0.9, 0.8]


def test_reranker_failure_is_converted_to_business_error() -> None:
    service = RetrievalService(
        OwnedRepository(), FakeEmbedding(), CandidateStore(), FailingReranker(), candidate_k=20
    )
    with pytest.raises(BusinessError) as error:
        service.search(
            owner_id=1,
            query="增值税优惠",
            knowledge_base_ids=[1],
            region="全国",
            query_date=date(2026, 8, 23),
            tax_type=None,
            taxpayer_type=None,
            top_k=2,
        )
    assert error.value.code == "RERANK_FAILED"


def test_empty_recall_skips_reranker() -> None:
    service = RetrievalService(
        OwnedRepository(), FakeEmbedding(), EmptyStore(), FailingReranker(), candidate_k=20
    )
    hits = service.search(
        owner_id=1,
        query="不存在的问题",
        knowledge_base_ids=[1],
        region="全国",
        query_date=date(2026, 8, 23),
        tax_type=None,
        taxpayer_type=None,
        top_k=5,
    )
    assert hits == []
