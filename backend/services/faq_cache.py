"""FAQ 精确命中 Redis 缓存。"""
import hashlib
import json
from typing import Protocol

from redis import Redis

# 版本号失效避免扫描和删除用户的全部 Query Key，写操作只需自增一次。


class FaqCache(Protocol):
    def get(self, owner_id: int, region: str, query: str) -> dict | None: ...

    def set(
        self, owner_id: int, region: str, query: str, value: dict, ttl_seconds: int
    ) -> None: ...

    def invalidate(self, owner_id: int) -> None: ...


class RedisFaqCache:
    def __init__(self, client: Redis):
        self.client = client

    @staticmethod
    def version_key(owner_id: int) -> str:
        return f"taxmind:faq:version:{owner_id}"

    def _version(self, owner_id: int) -> int:
        value = self.client.get(self.version_key(owner_id))
        return int(value or 0)

    def _key(self, owner_id: int, region: str, query: str) -> str:
        digest = hashlib.sha256(f"{region}:{query}".encode()).hexdigest()
        return f"taxmind:faq:route:{owner_id}:{self._version(owner_id)}:{digest}"

    def get(self, owner_id: int, region: str, query: str) -> dict | None:
        value = self.client.get(self._key(owner_id, region, query))
        if value is None:
            return None
        text = value.decode() if isinstance(value, bytes) else str(value)
        return json.loads(text)

    def set(
        self, owner_id: int, region: str, query: str, value: dict, ttl_seconds: int
    ) -> None:
        self.client.setex(
            self._key(owner_id, region, query),
            ttl_seconds,
            json.dumps(value, ensure_ascii=False),
        )

    def invalidate(self, owner_id: int) -> None:
        self.client.incr(self.version_key(owner_id))
