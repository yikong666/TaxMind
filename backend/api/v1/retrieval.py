"""Hybrid Retrieval 在线检索接口。"""

# 检索接口返回 Parent Context 及完整引用元数据，供后续 LLM 使用。
from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.api.dependencies import CurrentUser
from backend.api.v1.documents import get_embedding_provider, get_vector_store
from backend.core.config import get_settings
from backend.db.session import get_db
from backend.repositories.knowledge_base_repository import KnowledgeBaseRepository
from backend.schemas.common import ApiResponse
from backend.schemas.retrieval import RetrievalHitData, RetrievalRequest
from backend.services.retrieval import RetrievalService
from rag.reranking.bge_reranker import BgeReranker

router = APIRouter()


@lru_cache
def get_reranker() -> BgeReranker:
    settings = get_settings()
    return BgeReranker(
        settings.reranker_model_path,
        settings.reranker_device,
        settings.reranker_batch_size,
    )


def get_retrieval_service(
    session: Annotated[Session, Depends(get_db)],
) -> RetrievalService:
    settings = get_settings()
    return RetrievalService(
        KnowledgeBaseRepository(session),
        get_embedding_provider(),
        get_vector_store(),
        get_reranker(),
        settings.retrieval_candidate_k,
    )


RetrievalDependency = Annotated[RetrievalService, Depends(get_retrieval_service)]


@router.post("/search", response_model=ApiResponse[list[RetrievalHitData]])
def hybrid_search(
    request: RetrievalRequest,
    current_user: CurrentUser,
    service: RetrievalDependency,
) -> ApiResponse[list[RetrievalHitData]]:
    hits = service.search(owner_id=current_user.id, **request.model_dump())
    data = [
        RetrievalHitData(
            vector_id=hit.id,
            score=hit.rerank_score,
            hybrid_score=hit.hybrid_score,
            rerank_score=hit.rerank_score,
            child_id=hit.child_id,
            parent_id=hit.parent_id,
            document_id=hit.document_id,
            child_content=hit.text,
            parent_content=hit.parent_content,
            **hit.metadata,
        )
        for hit in hits
    ]
    return ApiResponse(data=data)
