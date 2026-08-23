"""知识库与文档数据访问。"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.models.document import Document
from backend.models.knowledge_base import KnowledgeBase, KnowledgeBaseType


class KnowledgeBaseRepository:
    def __init__(self, session: Session):
        self.session = session

    def get(self, knowledge_base_id: int, owner_id: int) -> KnowledgeBase | None:
        return self.session.scalar(
            select(KnowledgeBase).where(
                KnowledgeBase.id == knowledge_base_id, KnowledgeBase.owner_id == owner_id
            )
        )

    def get_by_name(self, name: str, owner_id: int) -> KnowledgeBase | None:
        return self.session.scalar(
            select(KnowledgeBase).where(
                KnowledgeBase.name == name, KnowledgeBase.owner_id == owner_id
            )
        )

    def list(self, owner_id: int) -> list[tuple[KnowledgeBase, int]]:
        statement = (
            select(KnowledgeBase, func.count(Document.id))
            .outerjoin(Document)
            .where(KnowledgeBase.owner_id == owner_id)
            .group_by(KnowledgeBase.id)
            .order_by(KnowledgeBase.created_at.desc())
        )
        return list(self.session.execute(statement).all())

    def create(
        self, owner_id: int, name: str, description: str, kb_type: KnowledgeBaseType
    ) -> KnowledgeBase:
        knowledge_base = KnowledgeBase(
            owner_id=owner_id, name=name, description=description, kb_type=kb_type
        )
        self.session.add(knowledge_base)
        self.session.commit()
        self.session.refresh(knowledge_base)
        return knowledge_base

    def save(self, knowledge_base: KnowledgeBase) -> KnowledgeBase:
        self.session.commit()
        self.session.refresh(knowledge_base)
        return knowledge_base

    def delete(self, knowledge_base: KnowledgeBase) -> None:
        self.session.delete(knowledge_base)
        self.session.commit()

    def add_document(self, document: Document) -> Document:
        self.session.add(document)
        self.session.commit()
        self.session.refresh(document)
        return document
