"""认证限流同时覆盖账号和客户端两个维度。"""

import pytest

from backend.core.config import Settings
from backend.core.exceptions import BusinessError
from backend.services.rate_limit import AuthRateLimiter


class MemoryRateLimitStore:
    def __init__(self) -> None:
        self.counts: dict[str, int] = {}

    def increment(self, key: str, window_seconds: int) -> int:
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]


def test_auth_rate_limit_rejects_requests_over_configured_threshold() -> None:
    settings = Settings(
        app_env="testing", auth_rate_limit_attempts=2, auth_rate_limit_window_seconds=60
    )
    limiter = AuthRateLimiter(MemoryRateLimitStore(), settings)
    limiter.check("login", "127.0.0.1", "tax_user")
    limiter.check("login", "127.0.0.1", "tax_user")
    with pytest.raises(BusinessError) as error:
        limiter.check("login", "127.0.0.1", "tax_user")
    assert error.value.status_code == 429
    assert error.value.code == "AUTH_RATE_LIMITED"
