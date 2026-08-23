"""FastAPI 应用工厂。"""

# 应用工厂便于测试环境替换数据库、缓存和对象存储依赖。
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.router import api_router
from backend.core.config import get_settings
from backend.core.exceptions import register_exception_handlers
from backend.core.logging import configure_logging, get_logger


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings)
    logger = get_logger(__name__)
    logger.info("TaxMind 后端服务启动，运行环境：%s", settings.app_env)
    yield
    logger.info("TaxMind 后端服务停止")


def create_app() -> FastAPI:
    """创建无外部连接副作用、便于测试的应用实例。"""
    settings = get_settings()
    configure_logging(settings)
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="企业级智能财税知识问答系统",
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url="/redoc" if settings.docs_enabled else None,
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_exception_handlers(application)
    application.include_router(api_router, prefix=settings.api_prefix)
    return application
