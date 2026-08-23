"""问题理解接口请求与响应结构。"""

# Query 长度在进入 LLM 前限制，避免异常超长输入占用模型上下文。
from pydantic import BaseModel, Field, field_validator

from rag.query_understanding.models import QueryUnderstandingResult


class QueryUnderstandingRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)

    @field_validator("query")
    @classmethod
    def normalize_query(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("问题不能为空")
        return normalized


class QueryUnderstandingData(QueryUnderstandingResult):
    pass
