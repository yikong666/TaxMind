"""文档解析、Chunk 预览与政策元数据接口。"""

# 大模型组件采用缓存单例，避免每次请求重复加载权重和连接 Milvus。
from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.api.dependencies import CurrentUser
from backend.core.config import get_settings
from backend.db.session import get_db
from backend.repositories.knowledge_base_repository import KnowledgeBaseRepository
from backend.schemas.common import ApiResponse
from backend.schemas.document_processing import (
    ParentChunkData,
    ParseRequest,
    ParseResult,
    PolicyMetadataData,
    PolicyMetadataUpdate,
    VectorIndexResult,
)
from backend.services.document_processing import DocumentProcessingService
from backend.services.storage import ObjectStorage, get_object_storage
from backend.services.vector_indexing import VectorIndexingService
from rag.embedding.bge_m3 import BgeM3EmbeddingProvider
from rag.vector.milvus_store import MilvusVectorStore

router = APIRouter()


def get_document_processing_service(
    session: Annotated[Session, Depends(get_db)],
    storage: Annotated[ObjectStorage, Depends(get_object_storage)],
) -> DocumentProcessingService:
    return DocumentProcessingService(KnowledgeBaseRepository(session), storage, get_settings())


ServiceDependency = Annotated[DocumentProcessingService, Depends(get_document_processing_service)]


@lru_cache
def get_embedding_provider() -> BgeM3EmbeddingProvider:
    settings = get_settings()
    return BgeM3EmbeddingProvider(settings.embedding_model_path, settings.embedding_device)


@lru_cache
def get_vector_store() -> MilvusVectorStore:
    settings = get_settings()
    return MilvusVectorStore(
        f"http://{settings.milvus_host}:{settings.milvus_port}",
        settings.milvus_database,
        settings.milvus_collection,
        settings.embedding_dense_dim,
    )


def get_vector_indexing_service(
    session: Annotated[Session, Depends(get_db)],
) -> VectorIndexingService:
    settings = get_settings()
    return VectorIndexingService(
        KnowledgeBaseRepository(session),
        get_embedding_provider(),
        get_vector_store(),
        settings.embedding_batch_size,
    )


VectorServiceDependency = Annotated[VectorIndexingService, Depends(get_vector_indexing_service)]


def to_parse_result(document, service: DocumentProcessingService) -> ParseResult:
    metadata_complete = bool(document.policy_metadata and document.policy_metadata.is_complete)
    return ParseResult(
        document_id=document.id,
        parse_status=document.parse_status,
        parse_error=document.parse_error,
        parent_chunk_count=document.parent_chunk_count,
        child_chunk_count=document.child_chunk_count,
        searchable=service.is_searchable(document),
        metadata_complete=metadata_complete,
    )


@router.post("/{document_id}/parse", response_model=ApiResponse[ParseResult])
def parse_document(
    document_id: int,
    request: ParseRequest,
    current_user: CurrentUser,
    service: ServiceDependency,
) -> ApiResponse[ParseResult]:
    document = service.parse(
        document_id,
        current_user.id,
        request.parent_chunk_size,
        request.child_chunk_size,
        request.chunk_overlap,
    )
    return ApiResponse(message="文档解析完成", data=to_parse_result(document, service))


@router.get("/{document_id}/chunks", response_model=ApiResponse[list[ParentChunkData]])
def list_chunks(
    document_id: int, current_user: CurrentUser, service: ServiceDependency
) -> ApiResponse[list[ParentChunkData]]:
    document = service.get_document(document_id, current_user.id)
    chunks = [
        ParentChunkData.model_validate(item, from_attributes=True)
        for item in document.parent_chunks
    ]
    return ApiResponse(data=chunks)


@router.put("/{document_id}/policy-metadata", response_model=ApiResponse[PolicyMetadataData])
def update_policy_metadata(
    document_id: int,
    request: PolicyMetadataUpdate,
    current_user: CurrentUser,
    service: ServiceDependency,
) -> ApiResponse[PolicyMetadataData]:
    values = request.model_dump()
    if values["source_url"] is not None:
        values["source_url"] = str(values["source_url"])
    metadata = service.update_policy_metadata(document_id, current_user.id, **values)
    data = PolicyMetadataData(
        **{
            field: getattr(metadata, field)
            for field in PolicyMetadataUpdate.model_fields
        },
        document_id=metadata.document_id,
        is_complete=metadata.is_complete,
    )
    return ApiResponse(message="政策元数据保存成功", data=data)


@router.post("/{document_id}/index", response_model=ApiResponse[VectorIndexResult])
def index_document(
    document_id: int,
    current_user: CurrentUser,
    service: VectorServiceDependency,
) -> ApiResponse[VectorIndexResult]:
    count = service.index(document_id, current_user.id)
    return ApiResponse(
        message="文档向量化完成",
        data=VectorIndexResult(
            document_id=document_id,
            indexed_count=count,
            vector_status="indexed",
        ),
    )
