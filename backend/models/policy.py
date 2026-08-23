"""税务政策元数据。"""
from datetime import date
from enum import StrEnum

from sqlalchemy import Date, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base, TimestampMixin


class PolicyStatus(StrEnum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REPLACED = "replaced"


class PolicyMetadata(TimestampMixin, Base):
    __tablename__ = "policy_metadata"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), unique=True, index=True
    )
    policy_title: Mapped[str | None] = mapped_column(String(500))
    doc_no: Mapped[str | None] = mapped_column(String(200), index=True)
    region: Mapped[str | None] = mapped_column(String(100), index=True)
    tax_type: Mapped[str | None] = mapped_column(String(100), index=True)
    taxpayer_type: Mapped[str | None] = mapped_column(String(100), index=True)
    publish_date: Mapped[date | None] = mapped_column(Date)
    effective_start: Mapped[date | None] = mapped_column(Date, index=True)
    effective_end: Mapped[date | None] = mapped_column(Date, index=True)
    policy_status: Mapped[PolicyStatus | None] = mapped_column(
        Enum(
            PolicyStatus,
            values_callable=lambda values: [item.value for item in values],
        ),
        index=True,
    )
    source_url: Mapped[str | None] = mapped_column(Text)
    document: Mapped["Document"] = relationship(back_populates="policy_metadata")  # noqa: F821

    @property
    def is_complete(self) -> bool:
        return all(
            [
                self.policy_title,
                self.doc_no,
                self.region,
                self.effective_start,
                self.policy_status,
                self.source_url,
            ]
        )
