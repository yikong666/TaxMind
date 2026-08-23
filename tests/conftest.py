# 测试应用使用临时 SQLite、内存验证码和对象存储，保证用例相互隔离。
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend.api.v1.auth import get_auth_service
from backend.app import create_app
from backend.core.config import get_settings
from backend.db.base import Base
from backend.db.session import get_db
from backend.repositories.user_repository import UserRepository
from backend.services.auth import AuthService
from backend.services.captcha import CaptchaService, CaptchaStore, get_captcha_service
from backend.services.storage import ObjectStorage, get_object_storage


class MemoryCaptchaStore(CaptchaStore):
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def save(self, captcha_id: str, code: str, ttl_seconds: int) -> None:
        self.values[captcha_id] = code

    def consume(self, captcha_id: str, code: str) -> bool:
        stored = self.values.pop(captcha_id, None)
        return stored is not None and stored.upper() == code.strip().upper()


class MemoryObjectStorage(ObjectStorage):
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def upload(self, object_key, stream, length: int, content_type: str) -> None:
        self.objects[object_key] = stream.read(length)

    def delete(self, object_key: str) -> None:
        self.objects.pop(object_key, None)

    def download(self, object_key: str) -> bytes:
        return self.objects[object_key]


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, tmp_path) -> TestClient:
    monkeypatch.setenv("APP_ENV", "testing")
    monkeypatch.setenv("LOG_FILE", str(tmp_path / "taxmind-test.log"))
    get_settings.cache_clear()
    app = create_app()
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = Session(engine, expire_on_commit=False)
    captcha_store = MemoryCaptchaStore()
    captcha_service = CaptchaService(captcha_store, get_settings())
    object_storage = MemoryObjectStorage()

    app.dependency_overrides[get_db] = lambda: session
    app.dependency_overrides[get_captcha_service] = lambda: captcha_service
    app.dependency_overrides[get_object_storage] = lambda: object_storage
    app.dependency_overrides[get_auth_service] = lambda: AuthService(
        UserRepository(session), captcha_service, get_settings()
    )
    with TestClient(app) as test_client:
        test_client.captcha_store = captcha_store  # type: ignore[attr-defined]
        test_client.object_storage = object_storage  # type: ignore[attr-defined]
        yield test_client
    session.close()
    engine.dispose()
    get_settings.cache_clear()
