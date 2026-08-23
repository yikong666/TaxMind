"""FAQ 管理与路由接口结构。"""
from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator, model_validator

# 日期范围在 API 边界校验，避免无效 FAQ 进入数据库和缓存。


class FaqFields(BaseModel):
    question: str = Field(min_length=2, max_length=500)
    answer: str = Field(min_length=2, max_length=10000)
    category: str = Field(default="未分类", max_length=100)
    region: str = Field(default="全国", min_length=1, max_length=100)
    doc_no: str | None = Field(default=None, max_length=200)
    effective_start: date | None = None
    effective_end: date | None = None
    is_enabled: bool = True

    @field_validator("question", "answer", "category", "region")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def validate_period(self):
        if self.effective_start and self.effective_end:
            if self.effective_end < self.effective_start:
                raise ValueError("失效日期不能早于生效日期")
        return self


class FaqCreate(FaqFields):
    pass


class FaqUpdate(BaseModel):
    question: str | None = Field(default=None, min_length=2, max_length=500)
    answer: str | None = Field(default=None, min_length=2, max_length=10000)
    category: str | None = Field(default=None, max_length=100)
    region: str | None = Field(default=None, min_length=1, max_length=100)
    doc_no: str | None = Field(default=None, max_length=200)
    effective_start: date | None = None
    effective_end: date | None = None
    is_enabled: bool | None = None


class FaqData(FaqFields):
    id: int
    created_at: datetime
    updated_at: datetime


class FaqRouteRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    region: str = Field(default="全国", min_length=1, max_length=100)
    query_date: date = Field(default_factory=date.today)


class FaqRouteResult(BaseModel):
    matched: bool
    continue_to_rag: bool
    source: str
    score: float
    faq: FaqData | None = None
