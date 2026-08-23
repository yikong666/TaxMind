import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend.api.v1.auth import get_auth_service
from backend.app import create_app
from backend.core.config import get_settings
from backend.db.base import Base
from backend.repositories.user_repository import UserRepository
from backend.services.auth import AuthService
from backend.services.captcha import CaptchaService, CaptchaStore, get_captcha_service


class MemoryCaptchaStore(CaptchaStore):
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def save(self, captcha_id: str, code: str, ttl_seconds: int) -> None:
        self.values[captcha_id] = code

    def consume(self, captcha_id: str, code: str) -> bool:
        stored = self.values.pop(captcha_id, None)
        return stored is not None and stored.upper() == code.strip().upper()


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

    app.dependency_overrides[get_captcha_service] = lambda: captcha_service
    app.dependency_overrides[get_auth_service] = lambda: AuthService(
        UserRepository(session), captcha_service, get_settings()
    )
    with TestClient(app) as test_client:
        test_client.captcha_store = captcha_store  # type: ignore[attr-defined]
        yield test_client
    session.close()
    engine.dispose()
    get_settings.cache_clear()
