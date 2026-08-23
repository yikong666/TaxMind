"""标题层级优先的 Parent-Child Chunk。"""
import re
from dataclasses import dataclass

from rag.parsing.document_parser import ParsedSection


@dataclass(frozen=True)
class ChunkDraft:
    heading: str | None
    content: str
    children: list[str]


class ParentChildChunker:
    def __init__(self, parent_size: int, child_size: int, overlap: int):
        if child_size > parent_size:
            raise ValueError("Child Chunk 大小不能超过 Parent Chunk")
        if overlap >= child_size:
            raise ValueError("Chunk overlap 必须小于 Child Chunk 大小")
        self.parent_size = parent_size
        self.child_size = child_size
        self.overlap = overlap

    def split(self, sections: list[ParsedSection]) -> list[ChunkDraft]:
        drafts: list[ChunkDraft] = []
        for section in sections:
            for parent_content in self._split_text(section.content, self.parent_size):
                children = self._split_text(parent_content, self.child_size)
                drafts.append(ChunkDraft(section.heading, parent_content, children))
        return drafts

    def _split_text(self, text: str, size: int) -> list[str]:
        if len(text) <= size:
            return [text]
        units = [part.strip() for part in re.split(r"(?<=[。！？；\n])", text) if part.strip()]
        chunks: list[str] = []
        current = ""
        for unit in units:
            while len(unit) > size:
                if current:
                    chunks.append(current)
                    current = ""
                chunks.append(unit[:size])
                unit = unit[size - self.overlap :]
            if current and len(current) + len(unit) > size:
                chunks.append(current)
                prefix = current[-self.overlap :] if self.overlap else ""
                current = prefix + unit
            else:
                current += unit
        if current:
            chunks.append(current)
        return chunks
