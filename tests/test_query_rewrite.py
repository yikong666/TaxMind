"""Query 改写策略、事实保真、失败降级与多路融合测试。"""

import json
from types import SimpleNamespace

from backend.services.query_rewrite import QueryRewriteService
from backend.services.retrieval import RetrievalService
from rag.query_rewrite.models import RewriteStrategy
from rag.vector.milvus_store import SearchHit


class FakeRewriteLlm:
    def __init__(self, result):
        self.result = result
        self.user_text = ""

    def complete_json(self, system_prompt: str, user_text: str) -> str:
        self.user_text = user_text
        if isinstance(self.result, Exception):
            raise self.result
        return json.dumps(self.result, ensure_ascii=False)


def understood():
    # SimpleNamespace 仅提供改写服务需要的 Query Understanding 字段。
    def value(text):
        return SimpleNamespace(value=text)

    return SimpleNamespace(
        intent=value("tax_policy"),
        region="重庆",
        taxpayer_type="小规模纳税人",
        tax_type="增值税",
        period="2026年第二季度",
        amount=200000,
        business_type="增值税申报",
    )


def history_item(role: str, content: str):
    return SimpleNamespace(role=SimpleNamespace(value=role), content=content)


def hit(vector_id: str, parent_id: int, score: float) -> SearchHit:
    return SearchHit(
        id=vector_id,
        hybrid_score=score,
        rerank_score=None,
        child_id=parent_id,
        parent_id=parent_id,
        document_id=parent_id,
        text=vector_id,
        parent_content=f"{vector_id} parent",
        metadata={},
    )


def test_history_rewrite_keeps_original_query_and_context() -> None:
    llm = FakeRewriteLlm(
        {
            "strategy": "history",
            "queries": ["重庆小规模纳税人季度销售额20万元增值税纳税义务"],
            "hypothetical_document": None,
        }
    )
    service = QueryRewriteService(llm)
    plan = service.rewrite(
        "要交税吗？",
        understood(),
        [history_item("user", "我是重庆小规模纳税人，季度销售额20万元")],
    )
    assert plan.strategy == RewriteStrategy.HISTORY
    assert plan.retrieval_queries[0] == "要交税吗？"
    assert "季度销售额20万元" in plan.retrieval_queries[1]
    assert "我是重庆小规模纳税人" in llm.user_text


def test_hyde_adds_hypothetical_document_only_for_retrieval() -> None:
    llm = FakeRewriteLlm(
        {
            "strategy": "hyde",
            "queries": ["重庆小规模纳税人增值税免税政策20万元"],
            "hypothetical_document": "重庆小规模纳税人销售额20万元适用增值税优惠政策。",
        }
    )
    plan = QueryRewriteService(llm).rewrite("重庆小规模开票20万元交税吗？", understood(), [])
    assert plan.strategy == RewriteStrategy.HYDE
    assert len(plan.retrieval_queries) == 3
    assert plan.retrieval_queries[-1].startswith("重庆小规模纳税人")


def test_multi_query_keeps_distinct_subquestions() -> None:
    llm = FakeRewriteLlm(
        {
            "strategy": "multi_query",
            "queries": [
                "重庆小规模纳税人增值税免税政策20万元",
                "重庆小规模纳税人增值税申报流程20万元",
            ],
            "hypothetical_document": None,
        }
    )
    plan = QueryRewriteService(llm).rewrite(
        "重庆小规模开票20万元是否免税以及如何申报？", understood(), []
    )
    assert plan.strategy == RewriteStrategy.MULTI_QUERY
    assert len(plan.retrieval_queries) == 3
    assert "免税政策" in plan.retrieval_queries[1]
    assert "申报流程" in plan.retrieval_queries[2]


def test_new_number_or_invalid_output_falls_back_to_direct() -> None:
    invented = FakeRewriteLlm(
        {
            "strategy": "simplification",
            "queries": ["重庆小规模纳税人季度销售额30万元增值税政策"],
            "hypothetical_document": None,
        }
    )
    plan = QueryRewriteService(invented).rewrite(
        "重庆小规模季度销售额20万元怎么交税？", understood(), []
    )
    assert plan.fallback_used is True
    assert plan.retrieval_queries == ["重庆小规模季度销售额20万元怎么交税？"]

    unavailable = QueryRewriteService(FakeRewriteLlm(RuntimeError("服务不可用"))).rewrite(
        "增值税政策", understood(), []
    )
    assert unavailable.strategy == RewriteStrategy.DIRECT
    assert unavailable.fallback_used is True


def test_rrf_fusion_deduplicates_and_rewards_cross_query_hits() -> None:
    first = [hit("shared", 1, 0.9), hit("first-only", 2, 0.8)]
    second = [hit("second-only", 3, 0.95), hit("shared", 1, 0.7)]
    fused = RetrievalService._fuse_hits([first, second])
    assert [item.id for item in fused] == ["shared", "second-only", "first-only"]
    assert len({item.id for item in fused}) == 3
