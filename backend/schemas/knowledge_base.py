"""知识库与文档接口结构。"""

# 对外仅暴露文档业务字段，不返回 MinIO object_key 等内部信息。
from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator

from backend.models.document import ParseStatus
from backend.models.knowledge_base import KnowledgeBaseType
from backend.models.policy import PolicyStatus


class KnowledgeBaseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=2000)
    kb_type: KnowledgeBaseType

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("知识库名称不能为空")
        return value


class KnowledgeBaseUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("知识库名称不能为空")
        return value


class PolicyMetadataBrief(BaseModel):
    """知识库详情页所需的政策元数据摘要。"""

    policy_title: str | None
    doc_no: str | None
    region: str | None
    tax_type: str | None
    taxpayer_type: str | None
    publish_date: date | None
    effective_start: date | None
    effective_end: date | None
    policy_status: PolicyStatus | None
    source_url: str | None
    is_complete: bool


class DocumentData(BaseModel):
    id: int
    original_name: str
    content_type: str
    file_size: int
    parse_status: ParseStatus
    parse_error: str | None
    parent_chunk_count: int
    child_chunk_count: int
    policy_metadata: PolicyMetadataBrief | None = None
    created_at: datetime


class KnowledgeBaseData(BaseModel):
    id: int
    name: str
    description: str
    kb_type: KnowledgeBaseType
    document_count: int = 0
    chunk_count: int = 0
    created_at: datetime
    updated_at: datetime


class KnowledgeBaseDetail(KnowledgeBaseData):
    documents: list[DocumentData] = Field(default_factory=list)
