"""知识库模型。"""
from enum import StrEnum

from sqlalchemy import Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base, TimestampMixin


class KnowledgeBaseType(StrEnum):
    PUBLIC_POLICY = "public_policy"
    LOCAL_POLICY = "local_policy"
    INTERNAL = "internal"


class KnowledgeBase(TimestampMixin, Base):
    __tablename__ = "knowledge_bases"
    __table_args__ = (UniqueConstraint("owner_id", "name", name="uq_kb_owner_name"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    kb_type: Mapped[KnowledgeBaseType] = mapped_column(
        Enum(KnowledgeBaseType, values_callable=lambda values: [item.value for item in values]),
        nullable=False,
    )
    documents: Mapped[list["Document"]] = relationship(  # noqa: F821
        back_populates="knowledge_base", cascade="all, delete-orphan"
    )
