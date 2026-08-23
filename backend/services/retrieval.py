"""BGE-M3 Hybrid Retrieval 与政策过滤服务。"""
import logging
from datetime import date

from backend.core.exceptions import BusinessError
from backend.repositories.knowledge_base_repository import KnowledgeBaseRepository
from rag.embedding.bge_m3 import EmbeddingProvider
from rag.retrieval.filters import build_metadata_filter
from rag.vector.milvus_store import SearchHit, VectorStore

logger = logging.getLogger("taxmind.retrieval")


class RetrievalService:
    def __init__(
        self,
        repository: KnowledgeBaseRepository,
        embedding: EmbeddingProvider,
        vector_store: VectorStore,
    ):
        self.repository = repository
        self.embedding = embedding
        self.vector_store = vector_store

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
        hits = self.vector_store.hybrid_search(
            vector.dense,
            vector.sparse,
            expression,
            top_k,
            max(top_k * 4, 20),
        )
        logger.info("混合检索完成 owner_id=%s top_k=%s hits=%s", owner_id, top_k, len(hits))
        return hits
