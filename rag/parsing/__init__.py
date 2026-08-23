# 解析器输出统一 Section，再交由 Parent-Child Chunker 处理。
from rag.parsing.document_parser import DocumentParser, ParsedSection

__all__ = ["DocumentParser", "ParsedSection"]
