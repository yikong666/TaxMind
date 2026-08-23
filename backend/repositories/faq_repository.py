"""FAQ 数据访问与有效候选过滤。"""

from __future__ import annotations

from datetime import date

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from backend.models.faq import Faq

# 地区与有效期先由 MySQL 过滤，减少进入 BM25 的无效候选数量。


class FaqRepository:
    def __init__(self, session: Session):
        self.session = session

    def get(self, faq_id: int, owner_id: int) -> Faq | None:
        return self.session.scalar(select(Faq).where(Faq.id == faq_id, Faq.owner_id == owner_id))

    def get_by_normalized_question(self, owner_id: int, question: str) -> Faq | None:
        return self.session.scalar(
            select(Faq).where(Faq.owner_id == owner_id, Faq.normalized_question == question)
        )

    def list(
        self,
        owner_id: int,
        keyword: str | None = None,
        category: str | None = None,
        region: str | None = None,
        is_enabled: bool | None = None,
    ) -> list[Faq]:
        statement = select(Faq).where(Faq.owner_id == owner_id)
        if keyword:
            pattern = f"%{keyword}%"
            statement = statement.where(
                or_(
                    Faq.question.ilike(pattern),
                    Faq.answer.ilike(pattern),
                    Faq.doc_no.ilike(pattern),
                )
            )
        if category:
            statement = statement.where(Faq.category == category)
        if region:
            statement = statement.where(Faq.region == region)
        if is_enabled is not None:
            statement = statement.where(Faq.is_enabled.is_(is_enabled))
        return list(self.session.scalars(statement.order_by(Faq.updated_at.desc())))

    def list_effective(self, owner_id: int, region: str, query_date: date) -> list[Faq]:
        regions = ["全国"] if region == "全国" else ["全国", region]
        statement = select(Faq).where(
            Faq.owner_id == owner_id,
            Faq.is_enabled.is_(True),
            Faq.region.in_(regions),
            or_(Faq.effective_start.is_(None), Faq.effective_start <= query_date),
            or_(Faq.effective_end.is_(None), Faq.effective_end >= query_date),
        )
        return list(self.session.scalars(statement))

    def save(self, faq: Faq) -> Faq:
        self.session.add(faq)
        self.session.commit()
        self.session.refresh(faq)
        return faq

    def delete(self, faq: Faq) -> None:
        self.session.delete(faq)
        self.session.commit()
