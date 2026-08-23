"""文档解析、Chunk 与政策元数据结构。"""
from datetime import date

from pydantic import BaseModel, Field, HttpUrl

from backend.models.chunk import VectorStatus
from backend.models.document import ParseStatus
from backend.models.policy import PolicyStatus


class ParseRequest(BaseModel):
    parent_chunk_size: int | None = Field(default=None, ge=300, le=5000)
    child_chunk_size: int | None = Field(default=None, ge=100, le=2000)
    chunk_overlap: int | None = Field(default=None, ge=0, le=500)


class ParseResult(BaseModel):
    document_id: int
    parse_status: ParseStatus
    parse_error: str | None
    parent_chunk_count: int
    child_chunk_count: int
    searchable: bool
    metadata_complete: bool


class ChildChunkData(BaseModel):
    id: int
    chunk_index: int
    content: str
    vector_status: str


class ParentChunkData(BaseModel):
    id: int
    chunk_index: int
    heading: str | None
    content: str
    children: list[ChildChunkData]


class PolicyMetadataUpdate(BaseModel):
    policy_title: str | None = Field(default=None, max_length=500)
    doc_no: str | None = Field(default=None, max_length=200)
    region: str | None = Field(default=None, max_length=100)
    tax_type: str | None = Field(default=None, max_length=100)
    taxpayer_type: str | None = Field(default=None, max_length=100)
    publish_date: date | None = None
    effective_start: date | None = None
    effective_end: date | None = None
    policy_status: PolicyStatus | None = None
    source_url: HttpUrl | None = None


class PolicyMetadataData(BaseModel):
    document_id: int
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


class VectorIndexResult(BaseModel):
    document_id: int
    indexed_count: int
    vector_status: VectorStatus
