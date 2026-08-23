"""基于 Redis 固定窗口的认证接口限流。"""

from typing import Protocol

from redis import Redis

from backend.core.config import Settings, get_settings
from backend.core.exceptions import BusinessError


class RateLimitStore(Protocol):
    def increment(self, key: str, window_seconds: int) -> int: ...


class RedisRateLimitStore:
    def __init__(self, client: Redis):
        self.client = client

    def increment(self, key: str, window_seconds: int) -> int:
        # 事务确保首次计数与过期时间一起写入，避免永久残留的限流键。
        with self.client.pipeline(transaction=True) as pipe:
            pipe.incr(key)
            pipe.expire(key, window_seconds, nx=True)
            count, _ = pipe.execute()
        return int(count)


class AuthRateLimiter:
    def __init__(self, store: RateLimitStore, settings: Settings):
        self.store = store
        self.settings = settings

    def check(self, action: str, client_key: str, username: str) -> None:
        """同时限制客户端和账号维度，降低验证码轮换后的撞库风险。"""
        identities = {f"client:{client_key or 'unknown'}", f"user:{username.lower()}"}
        for identity in identities:
            key = f"taxmind:auth-rate:{action}:{identity}"
            if self.store.increment(key, self.settings.auth_rate_limit_window_seconds) > (
                self.settings.auth_rate_limit_attempts
            ):
                raise BusinessError("请求过于频繁，请稍后再试", "AUTH_RATE_LIMITED", 429)


def get_auth_rate_limiter() -> AuthRateLimiter:
    settings = get_settings()
    client = Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        password=settings.redis_password.get_secret_value() or None,
        db=settings.redis_db,
        socket_timeout=2,
    )
    return AuthRateLimiter(RedisRateLimitStore(client), settings)
