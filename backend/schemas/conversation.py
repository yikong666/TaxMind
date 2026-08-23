"""会话、消息与流式问答接口结构。"""

from datetime import date, datetime

from pydantic import BaseModel, Field


# 模型参数设置安全范围，避免单次请求无限占用上下文和输出额度。
class ConversationCreate(BaseModel):
    title: str = Field(default="新会话", min_length=1, max_length=100)


class ConversationUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=100)


class MessageData(BaseModel):
    id: int
    role: str
    content: str
    status: str
    risk_level: str | None
    route_source: str | None
    model_name: str | None
    citations: list
    error_message: str | None
    created_at: datetime


class ConversationData(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime


class ConversationDetail(ConversationData):
    messages: list[MessageData]


class ChatRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    knowledge_base_ids: list[int] = Field(default_factory=list, max_length=20)
    region: str = "全国"
    query_date: date = Field(default_factory=date.today)
    model: str | None = None
    temperature: float = Field(default=0.2, ge=0, le=2)
    top_p: float = Field(default=0.8, gt=0, le=1)
    max_tokens: int = Field(default=2000, ge=100, le=8000)
    history_rounds: int = Field(default=5, ge=0, le=20)
