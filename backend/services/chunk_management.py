"""Chunk 编辑删除、旧向量清理和索引状态汇总服务。"""

import logging

from backend.core.exceptions import BusinessError
from backend.models.chunk import VectorStatus
from backend.repositories.knowledge_base_repository import KnowledgeBaseRepository
from rag.vector.milvus_store import VectorStore

logger = logging.getLogger("taxmind.chunk_management")


# 修改数据库前先清空 Milvus 文档向量，防止旧内容继续进入 RAG 上下文。
class ChunkManagementService:
    def __init__(
        self, repository: KnowledgeBaseRepository, vector_store: VectorStore | None = None
    ):
        self.repository = repository
        self.vector_store = vector_store

    def _clear_vectors(self, document_id: int) -> None:
        if self.vector_store is None:
            raise RuntimeError("Chunk 修改服务未配置向量存储")
        try:
            self.vector_store.replace_document(document_id, [])
        except Exception as exc:
            logger.exception("清理文档旧向量失败 document_id=%s", document_id)
            raise BusinessError(
                "旧向量清理失败，Chunk 未修改", "VECTOR_CLEANUP_FAILED", 500
            ) from exc

    def update_parent(self, chunk_id: int, owner_id: int, values: dict):
        parent = self.repository.get_parent_chunk(chunk_id, owner_id)
        if parent is None:
            raise BusinessError("Parent Chunk 不存在", "PARENT_CHUNK_NOT_FOUND", 404)
        self._clear_vectors(parent.document_id)
        if "heading" in values:
            parent.heading = values["heading"].strip() if values["heading"] else None
        if "content" in values:
            parent.content = values["content"].strip()
        self.repository.save_chunk_change(parent.document)
        logger.info("Parent Chunk 已修改 chunk_id=%s document_id=%s", parent.id, parent.document_id)
        return parent

    def update_child(self, chunk_id: int, owner_id: int, content: str):
        child = self.repository.get_child_chunk(chunk_id, owner_id)
        if child is None:
            raise BusinessError("Child Chunk 不存在", "CHILD_CHUNK_NOT_FOUND", 404)
        self._clear_vectors(child.parent.document_id)
        child.content = content.strip()
        self.repository.save_chunk_change(child.parent.document)
        logger.info(
            "Child Chunk 已修改 chunk_id=%s document_id=%s", child.id, child.parent.document_id
        )
        return child

    def delete_parent(self, chunk_id: int, owner_id: int) -> int:
        parent = self.repository.get_parent_chunk(chunk_id, owner_id)
        if parent is None:
            raise BusinessError("Parent Chunk 不存在", "PARENT_CHUNK_NOT_FOUND", 404)
        document_id = parent.document_id
        self._clear_vectors(document_id)
        self.repository.delete_parent_chunk(parent)
        logger.info("Parent Chunk 已删除 chunk_id=%s document_id=%s", chunk_id, document_id)
        return document_id

    def delete_child(self, chunk_id: int, owner_id: int) -> int:
        child = self.repository.get_child_chunk(chunk_id, owner_id)
        if child is None:
            raise BusinessError("Child Chunk 不存在", "CHILD_CHUNK_NOT_FOUND", 404)
        document_id = child.parent.document_id
        self._clear_vectors(document_id)
        self.repository.delete_child_chunk(child)
        logger.info("Child Chunk 已删除 chunk_id=%s document_id=%s", chunk_id, document_id)
        return document_id

    def vector_status(self, document_id: int, owner_id: int) -> dict:
        document = self.repository.get_document(document_id, owner_id)
        if document is None:
            raise BusinessError("文档不存在", "DOCUMENT_NOT_FOUND", 404)
        children = [child for parent in document.parent_chunks for child in parent.children]
        counts = {status: 0 for status in VectorStatus}
        for child in children:
            counts[child.vector_status] += 1
        total = len(children)
        return {
            "document_id": document.id,
            "total": total,
            "pending": counts[VectorStatus.PENDING],
            "indexed": counts[VectorStatus.INDEXED],
            "failed": counts[VectorStatus.FAILED],
            "needs_reindex": total > 0 and counts[VectorStatus.INDEXED] != total,
            "can_index": total > 0,
        }
