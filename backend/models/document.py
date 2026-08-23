"""上传文档及处理状态模型。"""
from enum import StrEnum

from sqlalchemy import BigInteger, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base, TimestampMixin


class ParseStatus(StrEnum):
    PENDING = "pending"
    PARSING = "parsing"
    COMPLETED = "completed"
    FAILED = "failed"


class Document(TimestampMixin, Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    knowledge_base_id: Mapped[int] = mapped_column(
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"), index=True
    )
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    object_key: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    parse_status: Mapped[ParseStatus] = mapped_column(
        Enum(ParseStatus, values_callable=lambda values: [item.value for item in values]),
        default=ParseStatus.PENDING,
        nullable=False,
        index=True,
    )
    parse_error: Mapped[str | None] = mapped_column(Text)
    parent_chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    child_chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    knowledge_base: Mapped["KnowledgeBase"] = relationship(back_populates="documents")  # noqa: F821
    policy_metadata: Mapped["PolicyMetadata | None"] = relationship(  # noqa: F821
        back_populates="document", cascade="all, delete-orphan", uselist=False
    )
    parent_chunks: Mapped[list["ParentChunk"]] = relationship(  # noqa: F821
        back_populates="document", cascade="all, delete-orphan", order_by="ParentChunk.chunk_index"
    )
