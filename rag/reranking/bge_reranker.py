"""bge-reranker-v2-m3 交叉编码重排序适配器。"""
from pathlib import Path
from typing import Protocol


class Reranker(Protocol):
    def score(self, query: str, passages: list[str]) -> list[float]: ...


class BgeReranker:
    """首次检索时才加载模型，避免后端启动被大模型阻塞。"""

    def __init__(self, model_path: Path, device: str = "cpu", batch_size: int = 8):
        self.model_path = model_path
        self.device = device
        self.batch_size = batch_size
        self._model = None

    def _get_model(self):
        if self._model is None:
            if not self.model_path.exists():
                raise FileNotFoundError(f"Reranker 模型不存在：{self.model_path}")
            # CrossEncoder 直接对 Query-Passage 文本对输出相关性分数。
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(str(self.model_path), device=self.device)
        return self._model

    def score(self, query: str, passages: list[str]) -> list[float]:
        if not passages:
            return []
        pairs = [(query, passage) for passage in passages]
        scores = self._get_model().predict(
            pairs,
            batch_size=self.batch_size,
            show_progress_bar=False,
        )
        return [float(value) for value in scores]
