"""Parent-Child 文档块模型。"""

# Child 保存向量状态，Parent 保存生成回答所需的完整语义上下文。
from enum import StrEnum

from sqlalchemy import Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base, TimestampMixin


class VectorStatus(StrEnum):
    PENDING = "pending"
    INDEXED = "indexed"
    FAILED = "failed"


class ParentChunk(TimestampMixin, Base):
    __tablename__ = "parent_chunks"
    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_parent_document_index"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    heading: Mapped[str | None] = mapped_column(String(500))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    document: Mapped["Document"] = relationship(back_populates="parent_chunks")  # noqa: F821
    children: Mapped[list["ChildChunk"]] = relationship(
        back_populates="parent", cascade="all, delete-orphan", order_by="ChildChunk.chunk_index"
    )


class ChildChunk(TimestampMixin, Base):
    __tablename__ = "child_chunks"
    __table_args__ = (
        UniqueConstraint("parent_id", "chunk_index", name="uq_child_parent_index"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    parent_id: Mapped[int] = mapped_column(
        ForeignKey("parent_chunks.id", ondelete="CASCADE"), index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    vector_status: Mapped[VectorStatus] = mapped_column(
        Enum(VectorStatus, values_callable=lambda values: [item.value for item in values]),
        default=VectorStatus.PENDING,
        index=True,
        nullable=False,
    )
    vector_id: Mapped[str | None] = mapped_column(String(100), unique=True)
    parent: Mapped[ParentChunk] = relationship(back_populates="children")
