"""启动就绪检查测试配置校验和 MinIO endpoint 解析。"""

from scripts.check_readiness import load_environment, parse_endpoint, validate_environment


def test_parse_endpoint_supports_explicit_and_default_ports() -> None:
    assert parse_endpoint("minio:9000", 9000) == ("minio", 9000)
    assert parse_endpoint("127.0.0.1", 9000) == ("127.0.0.1", 9000)


def test_readiness_rejects_placeholders_and_accepts_complete_config() -> None:
    assert validate_environment({"MYSQL_PASSWORD": "change_me"})
    environment = {
        key: "secure-value-2026"
        for key in ("MYSQL_PASSWORD", "REDIS_PASSWORD", "MINIO_ACCESS_KEY", "MINIO_SECRET_KEY")
    }
    environment.update({"JWT_SECRET_KEY": "x" * 32, "DASHSCOPE_API_KEY": "test-key"})
    assert validate_environment(environment) == []


def test_environment_file_is_loaded(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("MYSQL_PASSWORD", "process-wins")
    path = tmp_path / ".env"
    path.write_text("MYSQL_PASSWORD=file-value\nREDIS_PORT=6379\n", encoding="utf-8")
    values = load_environment(path)
    assert values["MYSQL_PASSWORD"] == "process-wins"
    assert values["REDIS_PORT"] == "6379"
