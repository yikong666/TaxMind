"""知识库管理和文档上传业务。"""

# 数据库记录与 MinIO 对象必须同步创建和清理，避免孤儿文件。
import os
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from backend.core.config import Settings
from backend.core.exceptions import BusinessError
from backend.models.document import Document
from backend.models.knowledge_base import KnowledgeBase, KnowledgeBaseType
from backend.repositories.knowledge_base_repository import KnowledgeBaseRepository
from backend.services.file_validation import validate_file_content
from backend.services.storage import ObjectStorage

SUPPORTED_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".ppt", ".pptx", ".md", ".txt", ".html",
    ".htm", ".jpg", ".jpeg", ".png", ".webp",
}


class KnowledgeBaseService:
    def __init__(
        self,
        repository: KnowledgeBaseRepository,
        storage: ObjectStorage,
        settings: Settings,
    ):
        self.repository = repository
        self.storage = storage
        self.settings = settings

    def create(
        self, owner_id: int, name: str, description: str, kb_type: KnowledgeBaseType
    ) -> KnowledgeBase:
        if self.repository.get_by_name(name, owner_id):
            raise BusinessError("知识库名称已存在", "KNOWLEDGE_BASE_EXISTS", 409)
        return self.repository.create(owner_id, name, description, kb_type)

    def get(self, knowledge_base_id: int, owner_id: int) -> KnowledgeBase:
        knowledge_base = self.repository.get(knowledge_base_id, owner_id)
        if knowledge_base is None:
            raise BusinessError("知识库不存在", "KNOWLEDGE_BASE_NOT_FOUND", 404)
        return knowledge_base

    def update(
        self, knowledge_base_id: int, owner_id: int, name: str | None, description: str | None
    ) -> KnowledgeBase:
        knowledge_base = self.get(knowledge_base_id, owner_id)
        if name is not None and name != knowledge_base.name:
            if self.repository.get_by_name(name, owner_id):
                raise BusinessError("知识库名称已存在", "KNOWLEDGE_BASE_EXISTS", 409)
            knowledge_base.name = name
        if description is not None:
            knowledge_base.description = description
        return self.repository.save(knowledge_base)

    def delete(self, knowledge_base_id: int, owner_id: int) -> None:
        knowledge_base = self.get(knowledge_base_id, owner_id)
        for document in knowledge_base.documents:
            self.storage.delete(document.object_key)
        self.repository.delete(knowledge_base)

    def upload(self, knowledge_base_id: int, owner_id: int, upload: UploadFile) -> Document:
        self.get(knowledge_base_id, owner_id)
        filename = Path(upload.filename or "").name
        extension = Path(filename).suffix.lower()
        if not filename or extension not in SUPPORTED_EXTENSIONS:
            raise BusinessError("不支持的文档格式", "UNSUPPORTED_FILE_TYPE")

        upload.file.seek(0, os.SEEK_END)
        file_size = upload.file.tell()
        upload.file.seek(0)
        if file_size <= 0:
            raise BusinessError("上传文件不能为空", "EMPTY_FILE")
        if file_size > self.settings.max_upload_size_mb * 1024 * 1024:
            raise BusinessError(
                f"单个文件不能超过 {self.settings.max_upload_size_mb}MB", "FILE_TOO_LARGE"
            )

        # 内容校验后恢复流位置，保证上传到 MinIO 的仍是完整原文件。
        content = upload.file.read()
        upload.file.seek(0)
        content_type = validate_file_content(extension, content)
        object_key = f"knowledge-bases/{knowledge_base_id}/{uuid4().hex}{extension}"
        self.storage.upload(object_key, upload.file, file_size, content_type)
        document = Document(
            knowledge_base_id=knowledge_base_id,
            original_name=filename,
            object_key=object_key,
            content_type=content_type,
            file_size=file_size,
        )
        try:
            return self.repository.add_document(document)
        except Exception:
            self.storage.delete(object_key)
            raise
