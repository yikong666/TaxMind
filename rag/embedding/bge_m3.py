"""BGE-M3 Dense/Sparse 向量化适配器。"""
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class HybridEmbedding:
    dense: list[float]
    sparse: dict[int, float]


class EmbeddingProvider(Protocol):
    def embed(self, texts: list[str]) -> list[HybridEmbedding]: ...


class BgeM3EmbeddingProvider:
    """延迟加载模型，避免应用启动时占用大量内存。"""

    def __init__(self, model_path: Path, device: str = "cpu"):
        self.model_path = model_path
        self.device = device
        self._model = None

    def _get_model(self):
        if self._model is None:
            if not self.model_path.exists():
                raise FileNotFoundError(f"BGE-M3 模型不存在：{self.model_path}")
            from milvus_model.hybrid import BGEM3EmbeddingFunction

            self._model = BGEM3EmbeddingFunction(
                model_name_or_path=str(self.model_path),
                device=self.device,
                use_fp16=self.device.startswith("cuda"),
            )
        return self._model

    @staticmethod
    def _sparse_row(row) -> dict[int, float]:
        if hasattr(row, "col"):
            indices, values = row.col, row.data
        else:
            indices, values = row.indices, row.data
        return {
            int(index): float(value)
            for index, value in zip(indices, values, strict=True)
        }

    def embed(self, texts: list[str]) -> list[HybridEmbedding]:
        if not texts:
            return []
        result = self._get_model()(texts)
        return [
            HybridEmbedding(
                dense=[float(value) for value in result["dense"][index]],
                sparse=self._sparse_row(result["sparse"][index]),
            )
            for index in range(len(texts))
        ]
