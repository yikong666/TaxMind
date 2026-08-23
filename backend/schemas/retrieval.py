"""混合检索接口结构。"""

# 同时返回召回分数与重排序分数，便于效果评估和问题排查。
from datetime import date

from pydantic import BaseModel, Field, field_validator


class RetrievalRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    knowledge_base_ids: list[int] = Field(min_length=1, max_length=20)
    region: str = Field(default="全国", min_length=1, max_length=100)
    query_date: date = Field(default_factory=date.today)
    tax_type: str | None = Field(default=None, max_length=100)
    taxpayer_type: str | None = Field(default=None, max_length=100)
    top_k: int = Field(default=5, ge=1, le=20)

    @field_validator("query", "region")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("字段不能为空")
        return value


class RetrievalHitData(BaseModel):
    vector_id: str
    score: float
    hybrid_score: float
    rerank_score: float
    child_id: int
    parent_id: int
    document_id: int
    child_content: str
    parent_content: str
    region: str = ""
    doc_no: str = ""
    tax_type: str = ""
    taxpayer_type: str = ""
    effective_start: int = 0
    effective_end: int = 0
    policy_status: str
    source_url: str = ""
