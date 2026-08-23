from fastapi import APIRouter

from backend.api.v1.auth import router as auth_router
from backend.api.v1.health import router as health_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["系统"])
api_router.include_router(auth_router, prefix="/auth", tags=["账号认证"])
