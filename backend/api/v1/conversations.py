"""会话管理与 SSE 流式问答接口。"""

import json
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.api.dependencies import CurrentUser
from backend.api.v1.documents import get_embedding_provider, get_vector_store
from backend.api.v1.faqs import get_faq_cache
from backend.api.v1.query_understanding import get_llm_client
from backend.api.v1.retrieval import get_reranker
from backend.core.config import get_settings
from backend.db.session import get_db
from backend.repositories.conversation_repository import ConversationRepository
from backend.repositories.faq_repository import FaqRepository
from backend.repositories.knowledge_base_repository import KnowledgeBaseRepository
from backend.repositories.review_repository import ReviewRepository
from backend.schemas.common import ApiResponse
from backend.schemas.conversation import (
    ChatRequest,
    ConversationCreate,
    ConversationData,
    ConversationDetail,
    ConversationUpdate,
    MessageData,
)
from backend.services.conversation import ConversationService
from backend.services.faq import FaqService
from backend.services.query_rewrite import QueryRewriteService
from backend.services.query_understanding import QueryUnderstandingService
from backend.services.rag_chat import RagChatService
from backend.services.retrieval import RetrievalService
from backend.services.review import ReviewService

# SSE 禁止代理缓冲，客户端可在首个 Token 到达时立即渲染。
router = APIRouter()


def service(session):
    return ConversationService(ConversationRepository(session))


def conversation_data(item):
    return ConversationData.model_validate(item, from_attributes=True)


@router.post("", response_model=ApiResponse[ConversationData], status_code=201)
def create(
    request: ConversationCreate, user: CurrentUser, session: Annotated[Session, Depends(get_db)]
):
    return ApiResponse(data=conversation_data(service(session).create(user.id, request.title)))


@router.get("", response_model=ApiResponse[list[ConversationData]])
def list_items(user: CurrentUser, session: Annotated[Session, Depends(get_db)]):
    return ApiResponse(data=[conversation_data(x) for x in service(session).list(user.id)])


@router.get("/{conversation_id}", response_model=ApiResponse[ConversationDetail])
def detail(conversation_id: int, user: CurrentUser, session: Annotated[Session, Depends(get_db)]):
    item = service(session).get(conversation_id, user.id)
    data = conversation_data(item).model_dump()
    data["messages"] = [MessageData.model_validate(x, from_attributes=True) for x in item.messages]
    return ApiResponse(data=ConversationDetail.model_validate(data))


@router.patch("/{conversation_id}", response_model=ApiResponse[ConversationData])
def rename(
    conversation_id: int,
    request: ConversationUpdate,
    user: CurrentUser,
    session: Annotated[Session, Depends(get_db)],
):
    return ApiResponse(
        data=conversation_data(service(session).rename(conversation_id, user.id, request.title))
    )


@router.delete("/{conversation_id}", response_model=ApiResponse[None])
def delete(conversation_id: int, user: CurrentUser, session: Annotated[Session, Depends(get_db)]):
    service(session).delete(conversation_id, user.id)
    return ApiResponse(message="会话删除成功")


@router.post("/{conversation_id}/messages/stream")
def stream_chat(
    conversation_id: int,
    request: ChatRequest,
    user: CurrentUser,
    session: Annotated[Session, Depends(get_db)],
):
    settings = get_settings()
    conversations = service(session)
    item = conversations.get(conversation_id, user.id)
    faq = FaqService(
        FaqRepository(session),
        get_faq_cache(),
        settings.faq_bm25_threshold,
        settings.faq_cache_ttl_seconds,
    )
    retrieval = RetrievalService(
        KnowledgeBaseRepository(session),
        get_embedding_provider(),
        get_vector_store(),
        get_reranker(),
        settings.retrieval_candidate_k,
    )
    orchestrator = RagChatService(
        conversations,
        QueryUnderstandingService(get_llm_client()),
        faq,
        retrieval,
        get_llm_client(),
        ReviewService(ReviewRepository(session)),
        QueryRewriteService(get_llm_client()),
    )

    def events():
        for event in orchestrator.stream(item, user.id, request):
            payload = json.dumps(event["data"], ensure_ascii=False)
            yield f"event: {event['event']}\ndata: {payload}\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )
