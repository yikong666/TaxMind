"""LLM 意图理解、完整性判断与保守风险升级服务。"""
import json
import logging
import re

from pydantic import ValidationError

from backend.core.exceptions import BusinessError
from rag.query_understanding.llm_client import StructuredLlmClient
from rag.query_understanding.models import (
    LlmUnderstanding,
    QueryIntent,
    QueryUnderstandingResult,
    RiskLevel,
)
from rag.query_understanding.normalization import normalize_tax_type, normalize_taxpayer_type
from rag.query_understanding.prompt import SYSTEM_PROMPT

logger = logging.getLogger("taxmind.query_understanding")

RISK_ORDER = {
    RiskLevel.LOW: 0,
    RiskLevel.MEDIUM: 1,
    RiskLevel.HIGH: 2,
    RiskLevel.PROHIBITED: 3,
}
PROHIBITED_PATTERNS = [
    r"(?:怎么|如何|帮我|怎样).{0,10}(?:逃税|偷税|虚开发票|隐瞒收入|做两套账)",
    r"(?:买|购买).{0,6}发票.{0,8}(?:抵税|入账)",
    r"不交税.{0,8}(?:方法|办法|技巧)",
]
HIGH_RISK_TERMS = ("税务稽查", "行政处罚", "刑事责任", "重大税收违法")
COMPLIANCE_CONTEXT_TERMS = ("举报", "识别", "防范", "避免", "处罚", "后果", "危害")

REQUIRED_FIELDS = {
    QueryIntent.TAX_CALCULATION: [
        "region", "taxpayer_type", "tax_type", "period", "business_type",
    ],
    QueryIntent.TAX_POLICY: ["region", "taxpayer_type", "tax_type", "period"],
    QueryIntent.FILING_OPERATION: ["region", "taxpayer_type", "tax_type", "period"],
    QueryIntent.INVOICE_OPERATION: ["region", "business_type"],
}
FIELD_LABELS = {
    "region": "适用地区",
    "taxpayer_type": "纳税人类型",
    "tax_type": "涉及税种",
    "period": "所属期",
    "business_type": "具体业务类型",
}


class QueryUnderstandingService:
    def __init__(self, llm_client: StructuredLlmClient):
        self.llm_client = llm_client

    def understand(self, query: str) -> QueryUnderstandingResult:
        try:
            raw = self.llm_client.complete_json(SYSTEM_PROMPT, query)
            # 严格按 JSON 解析，模型输出代码块或自然语言时直接失败，不做宽松猜测。
            understood = LlmUnderstanding.model_validate(json.loads(raw))
        except (json.JSONDecodeError, ValidationError, ValueError, IndexError) as exc:
            logger.warning("Query Understanding 结构化输出无效：%s", exc)
            raise BusinessError(
                "问题理解失败，请重新描述后再试", "QUERY_UNDERSTANDING_FAILED", 502
            ) from exc
        except Exception as exc:
            logger.exception("Query Understanding 模型调用失败")
            raise BusinessError(
                "问题理解服务暂不可用", "QUERY_UNDERSTANDING_UNAVAILABLE", 502
            ) from exc

        # LLM 可能返回英文枚举或口语别名，检索前统一为知识库中的中文元数据。
        understood.tax_type = normalize_tax_type(understood.tax_type)
        understood.taxpayer_type = normalize_taxpayer_type(understood.taxpayer_type)
        risk_level = self._conservative_risk(query, understood.risk_level)
        missing_fields = [
            field
            for field in REQUIRED_FIELDS.get(understood.intent, [])
            if getattr(understood, field) is None
        ]
        prohibited = risk_level == RiskLevel.PROHIBITED
        clarification = None
        if missing_fields and not prohibited:
            labels = "、".join(FIELD_LABELS[field] for field in missing_fields)
            clarification = f"为了给出准确答复，请补充：{labels}。"
        safety_message = None
        if prohibited:
            safety_message = (
                "该问题涉及违法违规操作，我不能提供实施方法；"
                "如需合规处理，请咨询税务机关或专业人员。"
            )
        result = QueryUnderstandingResult(
            **understood.model_dump(exclude={"risk_level"}),
            risk_level=risk_level,
            missing_fields=missing_fields,
            needs_clarification=bool(missing_fields) and not prohibited,
            clarification_question=clarification,
            safety_message=safety_message,
        )
        logger.info(
            "问题理解完成 intent=%s risk=%s missing=%s",
            result.intent,
            result.risk_level,
            result.missing_fields,
        )
        return result

    @staticmethod
    def _conservative_risk(query: str, llm_risk: RiskLevel) -> RiskLevel:
        # 规则只允许向更高风险升级，绝不覆盖模型给出的更严格等级。
        rule_risk = RiskLevel.LOW
        prohibited_match = any(
            re.search(pattern, query, re.IGNORECASE) for pattern in PROHIBITED_PATTERNS
        )
        compliance_context = any(term in query for term in COMPLIANCE_CONTEXT_TERMS)
        if prohibited_match and not compliance_context:
            rule_risk = RiskLevel.PROHIBITED
        elif any(term in query for term in HIGH_RISK_TERMS):
            rule_risk = RiskLevel.HIGH
        return max((llm_risk, rule_risk), key=RISK_ORDER.__getitem__)
