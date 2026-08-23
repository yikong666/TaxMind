"""Query Understanding 结构化模型与枚举。"""

# 枚举值作为后续检索策略和风险门禁的稳定内部协议。
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class QueryIntent(StrEnum):
    TAX_POLICY = "tax_policy"
    TAX_CALCULATION = "tax_calculation"
    FILING_OPERATION = "filing_operation"
    INVOICE_OPERATION = "invoice_operation"
    GENERAL_TAX = "general_tax"
    UNKNOWN = "unknown"


class RiskLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    PROHIBITED = "PROHIBITED"


class LlmUnderstanding(BaseModel):
    """LLM 必须返回的原始结构，额外字段会被忽略。"""

    intent: QueryIntent
    region: str | None
    taxpayer_type: str | None
    tax_type: str | None
    period: str | None
    amount: float | None = Field(ge=0)
    business_type: str | None
    risk_level: RiskLevel

    @field_validator("region", "taxpayer_type", "tax_type", "period", "business_type")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class QueryUnderstandingResult(LlmUnderstanding):
    missing_fields: list[str] = Field(default_factory=list)
    needs_clarification: bool = False
    clarification_question: str | None = None
    safety_message: str | None = None
