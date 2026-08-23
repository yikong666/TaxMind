"""知识库与文档数据访问。"""

# 所有读取均带 owner_id 条件，保证租户数据隔离。
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.models.chunk import ChildChunk, ParentChunk, VectorStatus
from backend.models.document import Document, ParseStatus
from backend.models.knowledge_base import KnowledgeBase, KnowledgeBaseType
from backend.models.policy import PolicyMetadata
from rag.vector.milvus_store import VectorRecord


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

    def get_document(self, document_id: int, owner_id: int) -> Document | None:
        return self.session.scalar(
            select(Document)
            .join(KnowledgeBase)
            .where(Document.id == document_id, KnowledgeBase.owner_id == owner_id)
        )

    def set_parse_status(
        self, document: Document, status: ParseStatus, error: str | None = None
    ) -> None:
        document.parse_status = status
        document.parse_error = error
        self.session.commit()

    def replace_chunks(self, document: Document, drafts, is_policy: bool) -> Document:
        for old_chunk in list(document.parent_chunks):
            self.session.delete(old_chunk)
        self.session.flush()
        parent_count = 0
        child_count = 0
        for parent_index, draft in enumerate(drafts):
            parent = ParentChunk(
                document_id=document.id,
                chunk_index=parent_index,
                heading=draft.heading,
                content=draft.content,
            )
            parent.children = [
                ChildChunk(chunk_index=index, content=content)
                for index, content in enumerate(draft.children)
            ]
            self.session.add(parent)
            parent_count += 1
            child_count += len(parent.children)
        if is_policy and document.policy_metadata is None:
            document.policy_metadata = PolicyMetadata(document_id=document.id)
        document.parent_chunk_count = parent_count
        document.child_chunk_count = child_count
        document.parse_status = ParseStatus.COMPLETED
        document.parse_error = None
        self.session.commit()
        self.session.refresh(document)
        return document

    def save_policy_metadata(self, metadata: PolicyMetadata) -> PolicyMetadata:
        self.session.commit()
        self.session.refresh(metadata)
        return metadata

    def set_vector_status(
        self,
        children: list[ChildChunk],
        status: VectorStatus,
        records: list[VectorRecord] | None = None,
    ) -> None:
        vector_ids = {item.child_id: item.id for item in records or []}
        for child in children:
            child.vector_status = status
            child.vector_id = vector_ids.get(child.id) if status == VectorStatus.INDEXED else None
        self.session.commit()
