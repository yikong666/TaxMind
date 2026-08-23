"""将 LLM 抽取的财税字段归一为知识库元数据使用的稳定中文值。"""

# 未知别名返回 None，避免不可靠的完全匹配条件把正确政策提前过滤掉。
TAX_TYPE_ALIASES = {
    "vat": "增值税",
    "增值税": "增值税",
    "cit": "企业所得税",
    "企业所得税": "企业所得税",
    "pit": "个人所得税",
    "个税": "个人所得税",
    "个人所得税": "个人所得税",
}
TAXPAYER_TYPE_ALIASES = {
    "small_scale": "小规模纳税人",
    "小规模": "小规模纳税人",
    "小规模纳税人": "小规模纳税人",
    "general_taxpayer": "一般纳税人",
    "一般纳税人": "一般纳税人",
    "individual": "自然人",
    "个人": "自然人",
    "自然人": "自然人",
    "enterprise": "企业",
    "企业": "企业",
}


def normalize_tax_type(value: str | None) -> str | None:
    """返回与政策元数据一致的税种，无法确认时取消硬过滤。"""
    return _normalize_alias(value, TAX_TYPE_ALIASES)


def normalize_taxpayer_type(value: str | None) -> str | None:
    """返回与政策元数据一致的纳税人类型，无法确认时取消硬过滤。"""
    return _normalize_alias(value, TAXPAYER_TYPE_ALIASES)


def _normalize_alias(value: str | None, aliases: dict[str, str]) -> str | None:
    if value is None:
        return None
    return aliases.get(value.strip().lower())
