"""文档 Child Chunk 向量化与 Milvus 入库服务。"""

# Child Chunk 负责召回，Parent Chunk 内容随向量一并保存供生成阶段使用。
import logging
from datetime import date

from backend.core.exceptions import BusinessError
from backend.models.chunk import ChildChunk, VectorStatus
from backend.models.document import Document
from backend.repositories.knowledge_base_repository import KnowledgeBaseRepository
from backend.services.document_processing import DocumentProcessingService
from rag.embedding.bge_m3 import EmbeddingProvider
from rag.vector.milvus_store import VectorRecord, VectorStore

logger = logging.getLogger("taxmind.vector_indexing")


def _date_number(value: date | None) -> int:
    return int(value.strftime("%Y%m%d")) if value else 0


class VectorIndexingService:
    def __init__(
        self,
        repository: KnowledgeBaseRepository,
        embedding: EmbeddingProvider,
        vector_store: VectorStore,
        batch_size: int,
    ):
        self.repository = repository
        self.embedding = embedding
        self.vector_store = vector_store
        self.batch_size = batch_size

    def index(self, document_id: int, owner_id: int) -> int:
        document = self.repository.get_document(document_id, owner_id)
        if document is None:
            raise BusinessError("文档不存在", "DOCUMENT_NOT_FOUND", 404)
        if not DocumentProcessingService.is_searchable(document):
            raise BusinessError("文档尚未完成解析或政策元数据不完整", "DOCUMENT_NOT_SEARCHABLE")
        children = [child for parent in document.parent_chunks for child in parent.children]
        if not children:
            raise BusinessError("文档没有可向量化的 Child Chunk", "DOCUMENT_HAS_NO_CHUNKS")
        try:
            records: list[VectorRecord] = []
            for offset in range(0, len(children), self.batch_size):
                batch = children[offset : offset + self.batch_size]
                vectors = self.embedding.embed([child.content for child in batch])
                if len(vectors) != len(batch):
                    raise ValueError("向量数量与 Child Chunk 数量不一致")
                records.extend(
                    self._record(document, child, vector.dense, vector.sparse)
                    for child, vector in zip(batch, vectors, strict=True)
                )
            self.vector_store.replace_document(document.id, records)
            self.repository.set_vector_status(children, VectorStatus.INDEXED, records)
            logger.info("文档向量化完成 document_id=%s chunks=%s", document.id, len(records))
            return len(records)
        except Exception as exc:
            self.repository.set_vector_status(children, VectorStatus.FAILED)
            logger.exception("文档向量化失败 document_id=%s", document.id)
            raise BusinessError(
                "文档向量化失败，请查看服务日志", "VECTOR_INDEX_FAILED", 500
            ) from exc

    @staticmethod
    def _record(
        document: Document,
        child: ChildChunk,
        dense: list[float],
        sparse: dict[int, float],
    ) -> VectorRecord:
        metadata = document.policy_metadata
        return VectorRecord(
            id=f"doc-{document.id}-child-{child.id}",
            child_id=child.id,
            parent_id=child.parent_id,
            document_id=document.id,
            knowledge_base_id=document.knowledge_base_id,
            owner_id=document.knowledge_base.owner_id,
            text=child.content,
            parent_content=child.parent.content,
            dense_vector=dense,
            sparse_vector=sparse,
            metadata={
                "policy_title": (
                    metadata.policy_title if metadata and metadata.policy_title else ""
                ),
                "original_name": document.original_name,
                "region": metadata.region if metadata and metadata.region else "",
                "doc_no": metadata.doc_no if metadata and metadata.doc_no else "",
                "tax_type": metadata.tax_type if metadata and metadata.tax_type else "",
                "taxpayer_type": (
                    metadata.taxpayer_type if metadata and metadata.taxpayer_type else ""
                ),
                "effective_start": _date_number(metadata.effective_start if metadata else None),
                "effective_end": _date_number(metadata.effective_end if metadata else None),
                "policy_status": (
                    metadata.policy_status.value
                    if metadata and metadata.policy_status
                    else "internal"
                ),
                "source_url": metadata.source_url if metadata and metadata.source_url else "",
            },
        )
