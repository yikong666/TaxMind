"""LLM Query Understanding 接口。"""
from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends

from backend.api.dependencies import CurrentUser
from backend.core.config import get_settings
from backend.core.exceptions import BusinessError
from backend.schemas.common import ApiResponse
from backend.schemas.query_understanding import (
    QueryUnderstandingData,
    QueryUnderstandingRequest,
)
from backend.services.query_understanding import QueryUnderstandingService
from rag.query_understanding.llm_client import DashScopeLlmClient

router = APIRouter()


@lru_cache
def get_llm_client() -> DashScopeLlmClient:
    settings = get_settings()
    api_key = settings.dashscope_api_key.get_secret_value()
    if not api_key:
        # 未配置密钥时明确返回服务不可用，不回退到伪造的规则分类结果。
        raise BusinessError("尚未配置 DASHSCOPE_API_KEY", "LLM_NOT_CONFIGURED", 503)
    return DashScopeLlmClient(
        api_key,
        settings.dashscope_base_url,
        settings.llm_model,
        settings.llm_timeout_seconds,
    )


def get_query_understanding_service() -> QueryUnderstandingService:
    return QueryUnderstandingService(get_llm_client())


QueryServiceDependency = Annotated[
    QueryUnderstandingService, Depends(get_query_understanding_service)
]


@router.post("/understand", response_model=ApiResponse[QueryUnderstandingData])
def understand_query(
    request: QueryUnderstandingRequest,
    _: CurrentUser,
    service: QueryServiceDependency,
) -> ApiResponse[QueryUnderstandingData]:
    result = service.understand(request.query)
    return ApiResponse(data=QueryUnderstandingData.model_validate(result.model_dump()))
