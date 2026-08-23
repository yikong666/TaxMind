"""Parent/Child Chunk 编辑与删除接口。"""

from fastapi import APIRouter

from backend.api.dependencies import CurrentUser
from backend.api.v1.documents import ChunkServiceDependency
from backend.schemas.chunk_management import ChildChunkUpdate, ParentChunkUpdate
from backend.schemas.common import ApiResponse
from backend.schemas.document_processing import ChildChunkData, ParentChunkData

# 修改任意 Chunk 都会使整篇文档的旧向量失效，随后可调用文档索引接口重建。
router = APIRouter()


@router.patch("/parents/{chunk_id}", response_model=ApiResponse[ParentChunkData])
def update_parent(
    chunk_id: int,
    request: ParentChunkUpdate,
    current_user: CurrentUser,
    service: ChunkServiceDependency,
):
    item = service.update_parent(chunk_id, current_user.id, request.model_dump(exclude_unset=True))
    return ApiResponse(
        message="Parent Chunk 修改成功",
        data=ParentChunkData.model_validate(item, from_attributes=True),
    )


@router.delete("/parents/{chunk_id}", response_model=ApiResponse[None])
def delete_parent(chunk_id: int, current_user: CurrentUser, service: ChunkServiceDependency):
    service.delete_parent(chunk_id, current_user.id)
    return ApiResponse(message="Parent Chunk 删除成功")


@router.patch("/children/{chunk_id}", response_model=ApiResponse[ChildChunkData])
def update_child(
    chunk_id: int,
    request: ChildChunkUpdate,
    current_user: CurrentUser,
    service: ChunkServiceDependency,
):
    item = service.update_child(chunk_id, current_user.id, request.content)
    return ApiResponse(
        message="Child Chunk 修改成功",
        data=ChildChunkData.model_validate(item, from_attributes=True),
    )


@router.delete("/children/{chunk_id}", response_model=ApiResponse[None])
def delete_child(chunk_id: int, current_user: CurrentUser, service: ChunkServiceDependency):
    service.delete_child(chunk_id, current_user.id)
    return ApiResponse(message="Child Chunk 删除成功")
