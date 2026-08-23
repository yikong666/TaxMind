"""FAQ 管理与优先路由接口。"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from redis import Redis
from sqlalchemy.orm import Session

from backend.api.dependencies import CurrentUser
from backend.core.config import get_settings
from backend.db.session import get_db
from backend.repositories.faq_repository import FaqRepository
from backend.schemas.common import ApiResponse
from backend.schemas.faq import FaqCreate, FaqData, FaqRouteRequest, FaqRouteResult, FaqUpdate
from backend.services.faq import FaqService
from backend.services.faq_cache import RedisFaqCache

# CRUD 和路由共用 Service，确保所有写操作都触发同一套缓存失效逻辑。

router = APIRouter()


def get_faq_cache() -> RedisFaqCache:
    settings = get_settings()
    client = Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        password=settings.redis_password.get_secret_value() or None,
        db=settings.redis_db,
        socket_timeout=2,
    )
    return RedisFaqCache(client)


def get_faq_service(
    session: Annotated[Session, Depends(get_db)],
) -> FaqService:
    settings = get_settings()
    return FaqService(
        FaqRepository(session),
        get_faq_cache(),
        settings.faq_bm25_threshold,
        settings.faq_cache_ttl_seconds,
    )


FaqServiceDependency = Annotated[FaqService, Depends(get_faq_service)]


def to_data(faq) -> FaqData:
    return FaqData.model_validate(faq, from_attributes=True)


@router.post("", response_model=ApiResponse[FaqData], status_code=201)
def create_faq(
    request: FaqCreate, current_user: CurrentUser, service: FaqServiceDependency
) -> ApiResponse[FaqData]:
    faq = service.create(current_user.id, **request.model_dump())
    return ApiResponse(message="FAQ 创建成功", data=to_data(faq))


@router.get("", response_model=ApiResponse[list[FaqData]])
def list_faqs(
    current_user: CurrentUser,
    service: FaqServiceDependency,
    keyword: Annotated[str | None, Query(max_length=200)] = None,
    category: Annotated[str | None, Query(max_length=100)] = None,
    region: Annotated[str | None, Query(max_length=100)] = None,
    is_enabled: bool | None = None,
) -> ApiResponse[list[FaqData]]:
    # 列表筛选在数据库执行，避免 FAQ 数量增长后把全部答案传到浏览器。
    items = service.list(
        current_user.id,
        keyword=keyword.strip() if keyword else None,
        category=category,
        region=region,
        is_enabled=is_enabled,
    )
    return ApiResponse(data=[to_data(item) for item in items])


@router.get("/{faq_id}", response_model=ApiResponse[FaqData])
def get_faq(
    faq_id: int, current_user: CurrentUser, service: FaqServiceDependency
) -> ApiResponse[FaqData]:
    return ApiResponse(data=to_data(service.get(faq_id, current_user.id)))


@router.patch("/{faq_id}", response_model=ApiResponse[FaqData])
def update_faq(
    faq_id: int,
    request: FaqUpdate,
    current_user: CurrentUser,
    service: FaqServiceDependency,
) -> ApiResponse[FaqData]:
    faq = service.update(faq_id, current_user.id, request.model_dump(exclude_unset=True))
    return ApiResponse(message="FAQ 更新成功", data=to_data(faq))


@router.delete("/{faq_id}", response_model=ApiResponse[None])
def delete_faq(
    faq_id: int, current_user: CurrentUser, service: FaqServiceDependency
) -> ApiResponse[None]:
    service.delete(faq_id, current_user.id)
    return ApiResponse(message="FAQ 删除成功")


@router.post("/route/match", response_model=ApiResponse[FaqRouteResult])
def route_faq(
    request: FaqRouteRequest,
    current_user: CurrentUser,
    service: FaqServiceDependency,
) -> ApiResponse[FaqRouteResult]:
    result = service.route(current_user.id, **request.model_dump())
    return ApiResponse(data=FaqRouteResult.model_validate(result))
