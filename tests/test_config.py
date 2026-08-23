# 配置测试确保非法环境名和非正数参数在应用启动前失败。
import pytest
from pydantic import ValidationError

from backend.core.config import Settings


def test_sensitive_values_are_loaded_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MYSQL_PASSWORD", "test-password")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-api-key")
    settings = Settings(_env_file=None)
    assert settings.mysql_password.get_secret_value() == "test-password"
    assert settings.dashscope_api_key.get_secret_value() == "test-api-key"
    assert "test-password" not in repr(settings)


def test_invalid_environment_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(app_env="unknown", _env_file=None)


def test_history_rounds_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        Settings(default_history_rounds=0, _env_file=None)
