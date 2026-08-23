"""检查 TaxMind 启动所需配置、模型目录与基础服务端口。"""

import json
import os
import socket
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVICES = {
    "MySQL": ("MYSQL_HOST", "MYSQL_PORT", 3306),
    "Redis": ("REDIS_HOST", "REDIS_PORT", 6379),
    "MinIO": ("MINIO_ENDPOINT", None, 9000),
    "Milvus": ("MILVUS_HOST", "MILVUS_PORT", 19530),
}


def load_environment(path: Path) -> dict[str, str]:
    """读取简单 KEY=VALUE 配置，进程环境变量拥有更高优先级。"""
    values: dict[str, str] = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            if line.strip() and not line.lstrip().startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip()
    values.update(os.environ)
    return values


def parse_endpoint(value: str, default_port: int) -> tuple[str, int]:
    host, separator, port = value.rpartition(":")
    return (host, int(port)) if separator else (value, default_port)


def validate_environment(environ: dict[str, str]) -> list[str]:
    errors = []
    for key in (
        "MYSQL_PASSWORD",
        "REDIS_PASSWORD",
        "MINIO_ACCESS_KEY",
        "MINIO_SECRET_KEY",
        "JWT_SECRET_KEY",
    ):
        value = environ.get(key, "")
        if not value or "请设置" in value or "change_me" in value:
            errors.append(f"{key} 未设置安全值")
    if len(environ.get("JWT_SECRET_KEY", "")) < 32:
        errors.append("JWT_SECRET_KEY 长度必须至少为 32")
    if not environ.get("DASHSCOPE_API_KEY"):
        errors.append("DASHSCOPE_API_KEY 未配置，在线问答将不可用")
    return errors


def port_open(host: str, port: int, timeout: float = 1.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def main() -> None:
    env = load_environment(ROOT / ".env")
    issues = validate_environment(env)
    checks = {}
    for name, (host_key, port_key, default_port) in SERVICES.items():
        raw_host = env.get(host_key, "127.0.0.1")
        if port_key is None:
            host, port = parse_endpoint(raw_host, default_port)
        else:
            host, port = raw_host, int(env.get(port_key, default_port))
        checks[name] = port_open(host, port)
    checks["BGE-M3"] = (ROOT / env.get("EMBEDDING_MODEL_PATH", "data/models/bge-m3")).exists()
    checks["Reranker"] = (
        ROOT / env.get("RERANKER_MODEL_PATH", "data/models/bge-reranker-v2-m3")
    ).exists()
    print(
        json.dumps(
            {"services": checks, "configuration_issues": issues}, ensure_ascii=False, indent=2
        )
    )
    if issues or not all(checks.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
