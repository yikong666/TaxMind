from fastapi import APIRouter

from backend.core.config import get_settings
from backend.schemas.common import ApiResponse
from backend.schemas.health import HealthData

router = APIRouter()


@router.get("/health", response_model=ApiResponse[HealthData], summary="检查服务状态")
async def health_check() -> ApiResponse[HealthData]:
    settings = get_settings()
    return ApiResponse(data=HealthData(status="healthy", version=settings.app_version))
