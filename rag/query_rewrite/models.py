"""Query 改写策略与结构化输出模型。"""

from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class RewriteStrategy(StrEnum):
    DIRECT = "direct"
    HISTORY = "history"
    EXPANSION = "expansion"
    SIMPLIFICATION = "simplification"
    HYDE = "hyde"
    MULTI_QUERY = "multi_query"


class LlmRewriteResult(BaseModel):
    """LLM 返回候选改写，服务层仍会执行事实保真校验。"""

    strategy: RewriteStrategy
    queries: list[str] = Field(min_length=1, max_length=5)
    hypothetical_document: str | None = Field(default=None, max_length=1200)

    @field_validator("queries")
    @classmethod
    def normalize_queries(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values if value.strip()]
        if not normalized:
            raise ValueError("至少需要一个有效检索 Query")
        return list(dict.fromkeys(normalized))


class QueryRewritePlan(BaseModel):
    strategy: RewriteStrategy
    retrieval_queries: list[str]
    fallback_used: bool = False
