"""跨模块 API 依赖。"""

# 鉴权依赖统一校验 JWT，并向下游接口提供当前用户。
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.core.config import get_settings
from backend.core.exceptions import BusinessError
from backend.core.security import decode_access_token
from backend.db.session import get_db
from backend.models.user import User
from backend.repositories.user_repository import UserRepository

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: Annotated[Session, Depends(get_db)],
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise BusinessError("请先登录", "NOT_AUTHENTICATED", 401)
    user_id = decode_access_token(credentials.credentials, get_settings())
    user = UserRepository(session).get_by_id(user_id) if user_id is not None else None
    if user is None or not user.is_active:
        raise BusinessError("登录状态无效或已过期", "INVALID_TOKEN", 401)
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
