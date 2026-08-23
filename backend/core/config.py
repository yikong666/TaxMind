"""统一配置管理，敏感配置仅从环境变量或 .env 读取。"""

# 所有外部服务地址和模型参数集中声明，禁止业务代码硬编码。
from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    app_name: str = "TaxMind 税智通"
    app_version: str = "0.1.0"
    app_env: str = "development"
    api_prefix: str = "/api/v1"
    docs_enabled: bool = True
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    log_level: str = "INFO"
    log_file: Path = PROJECT_ROOT / "logs" / "app.log"
    mysql_host: str = "127.0.0.1"
    mysql_port: int = 3306
    mysql_user: str = "taxmind"
    mysql_password: SecretStr = SecretStr("")
    mysql_database: str = "taxmind"
    jwt_secret_key: SecretStr = SecretStr("development-only-change-me")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 120
    captcha_expire_seconds: int = 300
    auth_rate_limit_attempts: int = 10
    auth_rate_limit_window_seconds: int = 300
    redis_host: str = "127.0.0.1"
    redis_port: int = 6379
    redis_password: SecretStr = SecretStr("")
    redis_db: int = 0
    milvus_host: str = "127.0.0.1"
    milvus_port: int = 19530
    milvus_database: str = "taxmind"
    milvus_collection: str = "taxmind_policy_chunks"
    minio_endpoint: str = "127.0.0.1:9000"
    minio_access_key: SecretStr = SecretStr("")
    minio_secret_key: SecretStr = SecretStr("")
    minio_bucket: str = "taxmind-documents"
    minio_secure: bool = False
    max_upload_size_mb: int = 50
    parent_chunk_size: int = 1200
    child_chunk_size: int = 300
    chunk_overlap: int = 50
    dashscope_api_key: SecretStr = SecretStr("")
    dashscope_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    llm_model: str = "qwen3-max"
    llm_timeout_seconds: int = 30
    embedding_model: str = "BAAI/bge-m3"
    embedding_model_path: Path = PROJECT_ROOT / "data" / "models" / "bge-m3"
    embedding_device: str = "cpu"
    embedding_batch_size: int = 8
    embedding_dense_dim: int = 1024
    reranker_model: str = "BAAI/bge-reranker-v2-m3"
    reranker_model_path: Path = PROJECT_ROOT / "data" / "models" / "bge-reranker-v2-m3"
    reranker_device: str = "cpu"
    reranker_batch_size: int = 8
    retrieval_candidate_k: int = 20
    default_top_k: int = 5
    default_history_rounds: int = 5
    faq_bm25_threshold: float = 0.85
    faq_cache_ttl_seconds: int = 3600

    @property
    def database_url(self) -> str:
        password = self.mysql_password.get_secret_value()
        return (
            f"mysql+pymysql://{self.mysql_user}:{password}@"
            f"{self.mysql_host}:{self.mysql_port}/{self.mysql_database}?charset=utf8mb4"
        )

    @field_validator("app_env")
    @classmethod
    def validate_environment(cls, value: str) -> str:
        allowed = {"development", "testing", "production"}
        if value not in allowed:
            raise ValueError(f"APP_ENV 必须是 {sorted(allowed)} 之一")
        return value

    @field_validator(
        "default_top_k",
        "default_history_rounds",
        "access_token_expire_minutes",
        "captcha_expire_seconds",
        "auth_rate_limit_attempts",
        "auth_rate_limit_window_seconds",
        "max_upload_size_mb",
        "parent_chunk_size",
        "child_chunk_size",
        "embedding_batch_size",
        "embedding_dense_dim",
        "reranker_batch_size",
        "retrieval_candidate_k",
        "llm_timeout_seconds",
        "faq_cache_ttl_seconds",
    )
    @classmethod
    def validate_positive_integer(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("数值必须大于 0")
        return value

    @field_validator("chunk_overlap")
    @classmethod
    def validate_overlap(cls, value: int) -> int:
        if value < 0:
            raise ValueError("Chunk overlap 不能小于 0")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
