# 业务路由在此集中配置前缀和中文 OpenAPI 标签。
from fastapi import APIRouter

from backend.api.v1.auth import router as auth_router
from backend.api.v1.conversations import router as conversation_router
from backend.api.v1.documents import router as document_router
from backend.api.v1.faqs import router as faq_router
from backend.api.v1.health import router as health_router
from backend.api.v1.knowledge_bases import router as knowledge_base_router
from backend.api.v1.query_understanding import router as query_understanding_router
from backend.api.v1.retrieval import router as retrieval_router
from backend.api.v1.reviews import router as review_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["系统"])
api_router.include_router(auth_router, prefix="/auth", tags=["账号认证"])
api_router.include_router(conversation_router, prefix="/conversations", tags=["会话与流式问答"])
api_router.include_router(knowledge_base_router, prefix="/knowledge-bases", tags=["知识库"])
api_router.include_router(document_router, prefix="/documents", tags=["文档解析"])
api_router.include_router(faq_router, prefix="/faqs", tags=["FAQ 管理与路由"])
api_router.include_router(retrieval_router, prefix="/retrieval", tags=["混合检索"])
api_router.include_router(review_router, tags=["回答反馈与人工工单"])
api_router.include_router(query_understanding_router, prefix="/query", tags=["问题理解与风险"])
