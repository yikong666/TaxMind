"""文档解析、分块及政策元数据确认。"""

# 政策文档只有解析完成且元数据完整后才允许进入检索链路。
from datetime import date

from backend.core.config import Settings
from backend.core.exceptions import BusinessError
from backend.models.document import Document, ParseStatus
from backend.models.knowledge_base import KnowledgeBaseType
from backend.models.policy import PolicyMetadata, PolicyStatus
from backend.repositories.knowledge_base_repository import KnowledgeBaseRepository
from backend.services.storage import ObjectStorage
from rag.parsing.chunker import ParentChildChunker
from rag.parsing.document_parser import DocumentParseError, DocumentParser


class DocumentProcessingService:
    def __init__(
        self,
        repository: KnowledgeBaseRepository,
        storage: ObjectStorage,
        settings: Settings,
        parser: DocumentParser | None = None,
    ):
        self.repository = repository
        self.storage = storage
        self.settings = settings
        self.parser = parser or DocumentParser()

    def get_document(self, document_id: int, owner_id: int) -> Document:
        document = self.repository.get_document(document_id, owner_id)
        if document is None:
            raise BusinessError("文档不存在", "DOCUMENT_NOT_FOUND", 404)
        return document

    def parse(
        self,
        document_id: int,
        owner_id: int,
        parent_size: int | None = None,
        child_size: int | None = None,
        overlap: int | None = None,
    ) -> Document:
        document = self.get_document(document_id, owner_id)
        self.repository.set_parse_status(document, ParseStatus.PARSING)
        try:
            content = self.storage.download(document.object_key)
            sections = self.parser.parse(document.original_name, content)
            chunker = ParentChildChunker(
                parent_size or self.settings.parent_chunk_size,
                child_size or self.settings.child_chunk_size,
                self.settings.chunk_overlap if overlap is None else overlap,
            )
            drafts = chunker.split(sections)
            if not drafts:
                raise DocumentParseError("文档分块结果为空")
            is_policy = document.knowledge_base.kb_type in {
                KnowledgeBaseType.PUBLIC_POLICY,
                KnowledgeBaseType.LOCAL_POLICY,
            }
            return self.repository.replace_chunks(document, drafts, is_policy)
        except (DocumentParseError, ValueError) as exc:
            self.repository.set_parse_status(document, ParseStatus.FAILED, str(exc))
            raise BusinessError(f"文档解析失败：{exc}", "DOCUMENT_PARSE_FAILED") from exc
        except Exception as exc:
            self.repository.set_parse_status(document, ParseStatus.FAILED, "解析服务异常")
            raise BusinessError(
                "文档解析失败，请查看服务日志", "DOCUMENT_PARSE_FAILED", 500
            ) from exc

    def update_policy_metadata(
        self,
        document_id: int,
        owner_id: int,
        *,
        policy_title: str | None,
        doc_no: str | None,
        region: str | None,
        tax_type: str | None,
        taxpayer_type: str | None,
        publish_date: date | None,
        effective_start: date | None,
        effective_end: date | None,
        policy_status: PolicyStatus | None,
        source_url: str | None,
    ) -> PolicyMetadata:
        document = self.get_document(document_id, owner_id)
        if document.knowledge_base.kb_type == KnowledgeBaseType.INTERNAL:
            raise BusinessError("企业内部知识库不使用政策元数据", "POLICY_METADATA_NOT_REQUIRED")
        metadata = document.policy_metadata or PolicyMetadata(document_id=document.id)
        if effective_start and effective_end and effective_end < effective_start:
            raise BusinessError("失效日期不能早于生效日期", "INVALID_EFFECTIVE_PERIOD")
        for field, value in locals().copy().items():
            if field in {
                "policy_title", "doc_no", "region", "tax_type", "taxpayer_type",
                "publish_date", "effective_start", "effective_end", "policy_status", "source_url",
            }:
                setattr(metadata, field, value.strip() if isinstance(value, str) else value)
        if metadata.id is None:
            document.policy_metadata = metadata
        return self.repository.save_policy_metadata(metadata)

    @staticmethod
    def is_searchable(document: Document) -> bool:
        if document.parse_status != ParseStatus.COMPLETED:
            return False
        if document.knowledge_base.kb_type == KnowledgeBaseType.INTERNAL:
            return True
        return bool(document.policy_metadata and document.policy_metadata.is_complete)
