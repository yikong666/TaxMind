"""验证码、注册和登录接口。"""

# 接口层仅完成参数映射，认证规则集中在 AuthService。
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from backend.core.config import get_settings
from backend.db.session import get_db
from backend.repositories.user_repository import UserRepository
from backend.schemas.auth import (
    CaptchaData,
    LoginRequest,
    RegisterRequest,
    TokenData,
    UserData,
)
from backend.schemas.common import ApiResponse
from backend.services.auth import AuthService
from backend.services.captcha import CaptchaService, get_captcha_service
from backend.services.rate_limit import AuthRateLimiter, get_auth_rate_limiter

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]
CaptchaServiceDependency = Annotated[CaptchaService, Depends(get_captcha_service)]
RateLimiterDependency = Annotated[AuthRateLimiter, Depends(get_auth_rate_limiter)]


def get_auth_service(
    session: DbSession,
    captcha_service: CaptchaServiceDependency,
    rate_limiter: RateLimiterDependency,
) -> AuthService:
    return AuthService(UserRepository(session), captcha_service, get_settings(), rate_limiter)


AuthServiceDependency = Annotated[AuthService, Depends(get_auth_service)]


@router.get("/captcha", response_model=ApiResponse[CaptchaData], summary="获取图形验证码")
def create_captcha(service: CaptchaServiceDependency) -> ApiResponse[CaptchaData]:
    challenge = service.create()
    return ApiResponse(data=CaptchaData(**challenge.__dict__))


@router.post("/register", response_model=ApiResponse[UserData], status_code=201, summary="注册账号")
def register(
    request: RegisterRequest, http_request: Request, service: AuthServiceDependency
) -> ApiResponse[UserData]:
    client_key = http_request.client.host if http_request.client else "unknown"
    user = service.register(**request.model_dump(), client_key=client_key)
    return ApiResponse(message="注册成功", data=UserData.model_validate(user, from_attributes=True))


@router.post("/login", response_model=ApiResponse[TokenData], summary="登录账号")
def login(
    request: LoginRequest, http_request: Request, service: AuthServiceDependency
) -> ApiResponse[TokenData]:
    client_key = http_request.client.host if http_request.client else "unknown"
    user, token, expires_in = service.login(**request.model_dump(), client_key=client_key)
    data = TokenData(
        access_token=token,
        expires_in=expires_in,
        user=UserData.model_validate(user, from_attributes=True),
    )
    return ApiResponse(message="登录成功", data=data)
