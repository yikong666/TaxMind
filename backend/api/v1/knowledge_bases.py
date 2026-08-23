"""知识库与文档接口。"""

# 文件流由 Service 校验后写入私有对象存储。
from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from backend.api.dependencies import CurrentUser
from backend.core.config import get_settings
from backend.db.session import get_db
from backend.repositories.knowledge_base_repository import KnowledgeBaseRepository
from backend.schemas.common import ApiResponse
from backend.schemas.knowledge_base import (
    DocumentData,
    KnowledgeBaseCreate,
    KnowledgeBaseData,
    KnowledgeBaseDetail,
    KnowledgeBaseUpdate,
)
from backend.services.knowledge_base import KnowledgeBaseService
from backend.services.storage import ObjectStorage, get_object_storage

router = APIRouter()


def get_knowledge_base_service(
    session: Annotated[Session, Depends(get_db)],
    storage: Annotated[ObjectStorage, Depends(get_object_storage)],
) -> KnowledgeBaseService:
    return KnowledgeBaseService(KnowledgeBaseRepository(session), storage, get_settings())


ServiceDependency = Annotated[KnowledgeBaseService, Depends(get_knowledge_base_service)]


def to_data(
    knowledge_base, document_count: int | None = None, chunk_count: int | None = None
) -> KnowledgeBaseData:
    return KnowledgeBaseData(
        id=knowledge_base.id,
        name=knowledge_base.name,
        description=knowledge_base.description,
        kb_type=knowledge_base.kb_type,
        document_count=(
            document_count if document_count is not None else len(knowledge_base.documents)
        ),
        chunk_count=(
            chunk_count
            if chunk_count is not None
            else sum(item.child_chunk_count for item in knowledge_base.documents)
        ),
        created_at=knowledge_base.created_at,
        updated_at=knowledge_base.updated_at,
    )


@router.post("", response_model=ApiResponse[KnowledgeBaseData], status_code=201)
def create_knowledge_base(
    request: KnowledgeBaseCreate, current_user: CurrentUser, service: ServiceDependency
) -> ApiResponse[KnowledgeBaseData]:
    knowledge_base = service.create(current_user.id, **request.model_dump())
    return ApiResponse(message="知识库创建成功", data=to_data(knowledge_base, 0, 0))


@router.get("", response_model=ApiResponse[list[KnowledgeBaseData]])
def list_knowledge_bases(
    current_user: CurrentUser, service: ServiceDependency
) -> ApiResponse[list[KnowledgeBaseData]]:
    items = [
        to_data(kb, document_count, chunk_count)
        for kb, document_count, chunk_count in service.repository.list(current_user.id)
    ]
    return ApiResponse(data=items)


@router.get("/{knowledge_base_id}", response_model=ApiResponse[KnowledgeBaseDetail])
def get_knowledge_base(
    knowledge_base_id: int, current_user: CurrentUser, service: ServiceDependency
) -> ApiResponse[KnowledgeBaseDetail]:
    knowledge_base = service.get(knowledge_base_id, current_user.id)
    base = to_data(knowledge_base)
    documents = [
        DocumentData.model_validate(item, from_attributes=True)
        for item in knowledge_base.documents
    ]
    return ApiResponse(data=KnowledgeBaseDetail(**base.model_dump(), documents=documents))


@router.patch("/{knowledge_base_id}", response_model=ApiResponse[KnowledgeBaseData])
def update_knowledge_base(
    knowledge_base_id: int,
    request: KnowledgeBaseUpdate,
    current_user: CurrentUser,
    service: ServiceDependency,
) -> ApiResponse[KnowledgeBaseData]:
    knowledge_base = service.update(
        knowledge_base_id, current_user.id, request.name, request.description
    )
    return ApiResponse(message="知识库修改成功", data=to_data(knowledge_base))


@router.delete("/{knowledge_base_id}", response_model=ApiResponse[None])
def delete_knowledge_base(
    knowledge_base_id: int, current_user: CurrentUser, service: ServiceDependency
) -> ApiResponse[None]:
    service.delete(knowledge_base_id, current_user.id)
    return ApiResponse(message="知识库删除成功")


@router.post(
    "/{knowledge_base_id}/documents",
    response_model=ApiResponse[list[DocumentData]],
    status_code=201,
)
def upload_documents(
    knowledge_base_id: int,
    current_user: CurrentUser,
    service: ServiceDependency,
    files: Annotated[list[UploadFile], File(description="支持一次上传多个文档")],
) -> ApiResponse[list[DocumentData]]:
    documents = [service.upload(knowledge_base_id, current_user.id, upload) for upload in files]
    return ApiResponse(
        message="文档上传成功",
        data=[DocumentData.model_validate(item, from_attributes=True) for item in documents],
    )
