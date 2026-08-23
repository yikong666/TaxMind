"""高频税务 FAQ 模型。"""

# normalized_question 用于同一用户内去重，原始问题保留给前端展示。
from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base, TimestampMixin


class Faq(TimestampMixin, Base):
    __tablename__ = "faqs"
    __table_args__ = (
        UniqueConstraint("owner_id", "normalized_question", name="uq_faq_owner_question"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    question: Mapped[str] = mapped_column(String(500), nullable=False)
    normalized_question: Mapped[str] = mapped_column(String(500), nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(100), default="未分类", nullable=False)
    region: Mapped[str] = mapped_column(String(100), default="全国", index=True, nullable=False)
    doc_no: Mapped[str | None] = mapped_column(String(200))
    effective_start: Mapped[date | None] = mapped_column(Date, index=True)
    effective_end: Mapped[date | None] = mapped_column(Date, index=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True, nullable=False)
