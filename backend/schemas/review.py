"""回答反馈、人工转交与工单接口结构。"""

from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from backend.models.review import FeedbackType, TicketStatus


# 点踩原因和人工处理结论限制长度，兼顾说明能力与数据库可控性。
class FeedbackCreate(BaseModel):
    feedback_type: FeedbackType
    reason: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def require_dislike_reason(self):
        if self.feedback_type == FeedbackType.DISLIKE and not (self.reason or "").strip():
            raise ValueError("点踩时必须填写反馈原因")
        return self


class HandoffCreate(BaseModel):
    reason: str | None = Field(default=None, max_length=1000)


class FeedbackData(BaseModel):
    id: int
    message_id: int
    feedback_type: FeedbackType
    reason: str | None
    created_at: datetime


class TicketUpdate(BaseModel):
    status: TicketStatus
    resolution: str | None = Field(default=None, max_length=4000)


class TicketData(BaseModel):
    id: int
    conversation_id: int
    message_id: int
    trigger_reason: str
    user_question: str
    ai_answer: str
    citations: list
    risk_level: str | None
    user_feedback: str | None
    status: TicketStatus
    resolution: str | None
    created_at: datetime
    updated_at: datetime
