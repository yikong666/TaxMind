"""图形验证码生成与 Redis 存储。"""

# 验证码仅存储摘要并一次性消费，接口不会返回明文答案。
import hashlib
import hmac
import html
import secrets
import string
from dataclasses import dataclass
from typing import Protocol
from uuid import uuid4

from redis import Redis

from backend.core.config import Settings, get_settings

CAPTCHA_ALPHABET = string.ascii_uppercase.replace("I", "").replace("O", "") + "23456789"


class CaptchaStore(Protocol):
    def save(self, captcha_id: str, code: str, ttl_seconds: int) -> None: ...

    def consume(self, captcha_id: str, code: str) -> bool: ...


class RedisCaptchaStore:
    def __init__(self, client: Redis):
        self.client = client

    @staticmethod
    def key(captcha_id: str) -> str:
        return f"taxmind:captcha:{captcha_id}"

    def save(self, captcha_id: str, code_digest: str, ttl_seconds: int) -> None:
        # Redis 泄露时也不能直接得到仍在有效期内的验证码明文。
        self.client.setex(self.key(captcha_id), ttl_seconds, code_digest)

    def consume(self, captcha_id: str, code: str) -> bool:
        key = self.key(captcha_id)
        stored = self.client.getdel(key)
        if stored is None:
            return False
        stored_digest = stored.decode() if isinstance(stored, bytes) else str(stored)
        return secrets.compare_digest(stored_digest, _captcha_digest(captcha_id, code))


def _captcha_digest(captcha_id: str, code: str) -> str:
    """将验证码 ID 作为盐生成稳定摘要，供一次性常量时间比较。"""
    normalized = code.strip().upper().encode("utf-8")
    return hmac.new(captcha_id.encode("utf-8"), normalized, hashlib.sha256).hexdigest()


@dataclass(frozen=True)
class CaptchaChallenge:
    captcha_id: str
    image_svg: str
    expires_in: int


class CaptchaService:
    def __init__(self, store: CaptchaStore, settings: Settings):
        self.store = store
        self.settings = settings

    def create(self) -> CaptchaChallenge:
        captcha_id = str(uuid4())
        code = "".join(secrets.choice(CAPTCHA_ALPHABET) for _ in range(6))
        self.store.save(
            captcha_id, _captcha_digest(captcha_id, code), self.settings.captcha_expire_seconds
        )
        return CaptchaChallenge(
            captcha_id=captcha_id,
            image_svg=self._render_svg(code),
            expires_in=self.settings.captcha_expire_seconds,
        )

    def verify(self, captcha_id: str, code: str) -> bool:
        return self.store.consume(captcha_id, code)

    @staticmethod
    def _render_svg(code: str) -> str:
        safe_code = html.escape(code)
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" width="120" height="42" '
            'viewBox="0 0 120 42">'
            '<rect width="120" height="42" rx="8" fill="#e8f4ef"/>'
            '<path d="M4 31L116 9M7 8L112 34" stroke="#93b9aa" opacity=".55"/>'
            f'<text x="60" y="29" text-anchor="middle" font-family="monospace" '
            f'font-size="24" font-weight="700" letter-spacing="5" fill="#174d3c">{safe_code}</text>'
            "</svg>"
        )


def get_captcha_store() -> CaptchaStore:
    settings = get_settings()
    client = Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        password=settings.redis_password.get_secret_value() or None,
        db=settings.redis_db,
        socket_timeout=2,
    )
    return RedisCaptchaStore(client)


def get_captcha_service() -> CaptchaService:
    return CaptchaService(get_captcha_store(), get_settings())
