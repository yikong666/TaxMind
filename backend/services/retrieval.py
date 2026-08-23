"""BGE-M3 Hybrid Retrieval 与政策过滤服务。"""

# 在线链路先做元数据过滤和混合召回，再重排序并构建 Parent Context。
import logging
from dataclasses import replace
from datetime import date

from backend.core.exceptions import BusinessError
from backend.repositories.knowledge_base_repository import KnowledgeBaseRepository
from rag.embedding.bge_m3 import EmbeddingProvider
from rag.reranking.bge_reranker import Reranker
from rag.retrieval.filters import build_metadata_filter
from rag.vector.milvus_store import SearchHit, VectorStore

logger = logging.getLogger("taxmind.retrieval")


class RetrievalService:
    def __init__(
        self,
        repository: KnowledgeBaseRepository,
        embedding: EmbeddingProvider,
        vector_store: VectorStore,
        reranker: Reranker,
        candidate_k: int,
    ):
        self.repository = repository
        self.embedding = embedding
        self.vector_store = vector_store
        self.reranker = reranker
        self.candidate_k = candidate_k

    def search(
        self,
        *,
        owner_id: int,
        query: str,
        knowledge_base_ids: list[int],
        region: str,
        query_date: date,
        tax_type: str | None,
        taxpayer_type: str | None,
        top_k: int,
    ) -> list[SearchHit]:
        for knowledge_base_id in knowledge_base_ids:
            if self.repository.get(knowledge_base_id, owner_id) is None:
                raise BusinessError("知识库不存在或无权访问", "KNOWLEDGE_BASE_NOT_FOUND", 404)
        vector = self.embedding.embed([query])[0]
        expression = build_metadata_filter(
            owner_id=owner_id,
            knowledge_base_ids=knowledge_base_ids,
            query_date=query_date,
            region=region,
            tax_type=tax_type,
            taxpayer_type=taxpayer_type,
        )
        candidate_limit = max(top_k, self.candidate_k)
        hits = self.vector_store.hybrid_search(
            vector.dense, vector.sparse, expression, candidate_limit, candidate_limit
        )
        if not hits:
            return []
        try:
            # Child Chunk 用于精确相关性判断，随后按 Parent 去重构建上下文。
            scores = self.reranker.score(query, [hit.text for hit in hits])
            if len(scores) != len(hits):
                raise ValueError("Reranker 分数数量与候选数量不一致")
            ranked = sorted(
                (
                    replace(hit, rerank_score=score)
                    for hit, score in zip(hits, scores, strict=True)
                ),
                key=lambda hit: hit.rerank_score or 0.0,
                reverse=True,
            )
        except Exception as exc:
            logger.exception("Reranker 重排序失败 owner_id=%s", owner_id)
            raise BusinessError("候选结果重排序失败", "RERANK_FAILED", 500) from exc
        # 同一 Parent 只保留分数最高的 Child，减少重复上下文占用。
        unique_hits: list[SearchHit] = []
        parent_ids: set[int] = set()
        for hit in ranked:
            if hit.parent_id not in parent_ids:
                unique_hits.append(hit)
                parent_ids.add(hit.parent_id)
            if len(unique_hits) == top_k:
                break
        logger.info(
            "混合检索与重排序完成 owner_id=%s candidates=%s contexts=%s",
            owner_id,
            len(hits),
            len(unique_hits),
        )
        return unique_hits
