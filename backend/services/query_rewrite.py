"""LLM Query 改写、结构校验与 Direct Retrieval 降级服务。"""

import json
import logging
import re

from pydantic import ValidationError

from rag.query_rewrite.models import LlmRewriteResult, QueryRewritePlan, RewriteStrategy
from rag.query_rewrite.prompt import SYSTEM_PROMPT
from rag.query_understanding.llm_client import StructuredLlmClient

logger = logging.getLogger("taxmind.query_rewrite")


# 原始 Query 永远保留在召回集合中，保证改写质量不佳时仍有基础召回结果。
class QueryRewriteService:
    def __init__(self, llm_client: StructuredLlmClient):
        self.llm_client = llm_client

    def rewrite(self, query: str, understood, history: list) -> QueryRewritePlan:
        history_text = [
            {"role": item.role.value, "content": item.content}
            for item in history[-6:]
            if item.content
        ]
        payload = {
            "query": query,
            "intent": understood.intent.value,
            "region": understood.region,
            "taxpayer_type": understood.taxpayer_type,
            "tax_type": understood.tax_type,
            "period": understood.period,
            "amount": understood.amount,
            "business_type": understood.business_type,
            "history": history_text,
        }
        try:
            raw = self.llm_client.complete_json(
                SYSTEM_PROMPT, json.dumps(payload, ensure_ascii=False)
            )
            result = LlmRewriteResult.model_validate(json.loads(raw))
            self._validate_facts(query, history_text, result)
            queries = [query, *result.queries]
            if result.strategy == RewriteStrategy.HYDE and result.hypothetical_document:
                queries.append(result.hypothetical_document)
            queries = list(dict.fromkeys(item.strip() for item in queries if item.strip()))[:6]
            logger.info("Query 改写完成 strategy=%s queries=%s", result.strategy, len(queries))
            return QueryRewritePlan(strategy=result.strategy, retrieval_queries=queries)
        except (json.JSONDecodeError, ValidationError, ValueError, TypeError, AttributeError):
            logger.exception("Query 改写输出无效，降级为 Direct Retrieval")
        except Exception:
            logger.exception("Query 改写服务不可用，降级为 Direct Retrieval")
        return QueryRewritePlan(
            strategy=RewriteStrategy.DIRECT,
            retrieval_queries=[query],
            fallback_used=True,
        )

    @staticmethod
    def _validate_facts(query: str, history: list[dict], result: LlmRewriteResult) -> None:
        source = query + " " + " ".join(item["content"] for item in history)
        rewritten = " ".join(result.queries) + " " + (result.hypothetical_document or "")
        source_numbers = set(re.findall(r"\d+(?:\.\d+)?", source))
        rewritten_numbers = set(re.findall(r"\d+(?:\.\d+)?", rewritten))
        query_numbers = set(re.findall(r"\d+(?:\.\d+)?", query))
        # 数字通常代表金额、税率或期间：既不能丢失原问题数字，也不能凭空新增。
        if not query_numbers.issubset(rewritten_numbers):
            raise ValueError("改写遗漏原问题中的数字事实")
        if not rewritten_numbers.issubset(source_numbers):
            raise ValueError("改写引入了来源中不存在的数字事实")
