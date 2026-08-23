import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.core.config import get_settings


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, tmp_path) -> TestClient:
    monkeypatch.setenv("APP_ENV", "testing")
    monkeypatch.setenv("LOG_FILE", str(tmp_path / "taxmind-test.log"))
    get_settings.cache_clear()
    with TestClient(create_app()) as test_client:
        yield test_client
    get_settings.cache_clear()
