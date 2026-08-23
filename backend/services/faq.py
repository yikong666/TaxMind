"""FAQ CRUD、缓存失效与 BM25 优先路由。"""
import logging
import re
from datetime import date

import jieba
from rank_bm25 import BM25Okapi

from backend.core.exceptions import BusinessError
from backend.models.faq import Faq
from backend.repositories.faq_repository import FaqRepository
from backend.services.faq_cache import FaqCache

logger = logging.getLogger("taxmind.faq")
STOP_WORDS = {"的", "了", "吗", "呢", "要", "请问", "怎么", "如何", "一下"}


def normalize_question(text: str) -> str:
    """统一大小写、空白和标点，供去重与精确缓存使用。"""
    return re.sub(r"[^\w\u4e00-\u9fff]+", "", text.lower())


def tokenize(text: str) -> list[str]:
    # 去除问句虚词，BM25 更关注税种、纳税人和具体业务术语。
    return [
        token.lower()
        for token in jieba.lcut(text)
        if token.strip() and token not in STOP_WORDS and not re.fullmatch(r"\W+", token)
    ]


class FaqService:
    def __init__(
        self,
        repository: FaqRepository,
        cache: FaqCache,
        threshold: float,
        cache_ttl_seconds: int,
    ):
        self.repository = repository
        self.cache = cache
        self.threshold = threshold
        self.cache_ttl_seconds = cache_ttl_seconds

    def create(self, owner_id: int, **values) -> Faq:
        normalized = normalize_question(values["question"])
        if self.repository.get_by_normalized_question(owner_id, normalized):
            raise BusinessError("FAQ 问题已存在", "FAQ_EXISTS", 409)
        faq = self.repository.save(
            Faq(owner_id=owner_id, normalized_question=normalized, **values)
        )
        self._invalidate(owner_id)
        logger.info("FAQ 创建成功 faq_id=%s owner_id=%s", faq.id, owner_id)
        return faq

    def list(self, owner_id: int) -> list[Faq]:
        return self.repository.list(owner_id)

    def get(self, faq_id: int, owner_id: int) -> Faq:
        faq = self.repository.get(faq_id, owner_id)
        if faq is None:
            raise BusinessError("FAQ 不存在", "FAQ_NOT_FOUND", 404)
        return faq

    def update(self, faq_id: int, owner_id: int, values: dict) -> Faq:
        faq = self.get(faq_id, owner_id)
        if values.get("question") is not None:
            normalized = normalize_question(values["question"])
            duplicate = self.repository.get_by_normalized_question(owner_id, normalized)
            if duplicate and duplicate.id != faq.id:
                raise BusinessError("FAQ 问题已存在", "FAQ_EXISTS", 409)
            values["normalized_question"] = normalized
        for field, value in values.items():
            setattr(faq, field, value.strip() if isinstance(value, str) else value)
        if faq.effective_start and faq.effective_end and faq.effective_end < faq.effective_start:
            raise BusinessError("失效日期不能早于生效日期", "INVALID_EFFECTIVE_PERIOD")
        saved = self.repository.save(faq)
        self._invalidate(owner_id)
        return saved

    def delete(self, faq_id: int, owner_id: int) -> None:
        faq = self.get(faq_id, owner_id)
        self.repository.delete(faq)
        self._invalidate(owner_id)

    def route(self, owner_id: int, query: str, region: str, query_date: date) -> dict:
        normalized = normalize_question(query)
        # 查询日期进入缓存键，避免跨年度返回已经失效的历史 FAQ。
        cache_query = f"{query_date.isoformat()}:{normalized}"
        cached = self._cache_get(owner_id, region, cache_query)
        if cached is not None:
            cached["source"] = "redis"
            return cached

        candidates = self.repository.list_effective(owner_id, region, query_date)
        if not candidates:
            return self._miss()
        query_tokens = tokenize(query)
        if not query_tokens:
            return self._miss()
        corpus = [tokenize(item.question) for item in candidates]
        raw_scores = BM25Okapi(corpus).get_scores(query_tokens)
        max_raw = max((float(score) for score in raw_scores), default=0.0)
        scored: list[tuple[float, Faq]] = []
        query_set = set(query_tokens)
        for faq, tokens, raw_score in zip(candidates, corpus, raw_scores, strict=True):
            if faq.normalized_question == normalized:
                score = 1.0
            else:
                coverage = len(query_set.intersection(tokens)) / len(query_set)
                bm25_ratio = max(float(raw_score), 0.0) / max_raw if max_raw > 0 else 1.0
                score = coverage * bm25_ratio
            scored.append((score, faq))
        score, best = max(scored, key=lambda item: item[0])
        if score < self.threshold:
            logger.info("FAQ 未命中 owner_id=%s score=%.4f", owner_id, score)
            return self._miss(score)
        result = {
            "matched": True,
            "continue_to_rag": False,
            "source": "mysql_bm25",
            "score": round(score, 6),
            "faq": self._faq_dict(best),
        }
        self._cache_set(owner_id, region, cache_query, result)
        return result

    @staticmethod
    def _faq_dict(faq: Faq) -> dict:
        return {
            "id": faq.id,
            "question": faq.question,
            "answer": faq.answer,
            "category": faq.category,
            "region": faq.region,
            "doc_no": faq.doc_no,
            "effective_start": faq.effective_start.isoformat() if faq.effective_start else None,
            "effective_end": faq.effective_end.isoformat() if faq.effective_end else None,
            "is_enabled": faq.is_enabled,
            "created_at": faq.created_at.isoformat(),
            "updated_at": faq.updated_at.isoformat(),
        }

    @staticmethod
    def _miss(score: float = 0.0) -> dict:
        return {
            "matched": False,
            "continue_to_rag": True,
            "source": "rag",
            "score": round(score, 6),
            "faq": None,
        }

    def _cache_get(self, owner_id: int, region: str, query: str) -> dict | None:
        try:
            return self.cache.get(owner_id, region, query)
        except Exception:
            logger.exception("FAQ Redis 读取失败，继续使用 MySQL/BM25")
            return None

    def _cache_set(self, owner_id: int, region: str, query: str, value: dict) -> None:
        try:
            self.cache.set(owner_id, region, query, value, self.cache_ttl_seconds)
        except Exception:
            logger.exception("FAQ Redis 写入失败，不影响当前命中结果")

    def _invalidate(self, owner_id: int) -> None:
        try:
            self.cache.invalidate(owner_id)
        except Exception:
            logger.exception("FAQ Redis 失效失败")
