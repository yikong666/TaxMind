"""Chunk 编辑及文档向量状态汇总结构。"""

from pydantic import BaseModel, Field, model_validator


# PATCH 至少包含一个字段，空字符串正文会导致无法形成有效检索内容。
class ParentChunkUpdate(BaseModel):
    heading: str | None = Field(default=None, max_length=500)
    content: str | None = Field(default=None, min_length=1, max_length=100000)

    @model_validator(mode="after")
    def require_change(self):
        if "heading" not in self.model_fields_set and "content" not in self.model_fields_set:
            raise ValueError("至少需要修改一个字段")
        if self.content is not None and not self.content.strip():
            raise ValueError("Parent Chunk 正文不能为空")
        return self


class ChildChunkUpdate(BaseModel):
    content: str = Field(min_length=1, max_length=50000)


class VectorStatusSummary(BaseModel):
    document_id: int
    total: int
    pending: int
    indexed: int
    failed: int
    needs_reindex: bool
    can_index: bool
