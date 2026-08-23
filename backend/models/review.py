"""回答反馈与人工审核工单模型。"""

# 反馈与工单独立保存，避免人工处理状态污染原始聊天消息。
from enum import StrEnum

from sqlalchemy import JSON, Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base, TimestampMixin


class FeedbackType(StrEnum):
    LIKE = "like"
    DISLIKE = "dislike"


class TicketStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    RESOLVED = "resolved"


class MessageFeedback(TimestampMixin, Base):
    __tablename__ = "message_feedbacks"
    __table_args__ = (UniqueConstraint("owner_id", "message_id", name="uq_feedback_owner_message"),)
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    message_id: Mapped[int] = mapped_column(
        ForeignKey("chat_messages.id", ondelete="CASCADE"), index=True
    )
    feedback_type: Mapped[FeedbackType] = mapped_column(
        Enum(FeedbackType, values_callable=lambda values: [item.value for item in values]),
        nullable=False,
    )
    reason: Mapped[str | None] = mapped_column(Text)


class ReviewTicket(TimestampMixin, Base):
    __tablename__ = "review_tickets"
    __table_args__ = (UniqueConstraint("owner_id", "message_id", name="uq_ticket_owner_message"),)
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    message_id: Mapped[int] = mapped_column(
        ForeignKey("chat_messages.id", ondelete="CASCADE"), index=True
    )
    trigger_reason: Mapped[str] = mapped_column(String(30), nullable=False)
    user_question: Mapped[str] = mapped_column(Text, nullable=False)
    ai_answer: Mapped[str] = mapped_column(Text, nullable=False)
    citations: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    risk_level: Mapped[str | None] = mapped_column(String(20))
    user_feedback: Mapped[str | None] = mapped_column(Text)
    status: Mapped[TicketStatus] = mapped_column(
        Enum(TicketStatus, values_callable=lambda values: [item.value for item in values]),
        default=TicketStatus.PENDING,
        nullable=False,
    )
    resolution: Mapped[str | None] = mapped_column(Text)
