"""Milvus 政策时效、地区与租户隔离过滤表达式。"""
from datetime import date


def _quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def build_metadata_filter(
    *,
    owner_id: int,
    knowledge_base_ids: list[int],
    query_date: date,
    region: str,
    tax_type: str | None = None,
    taxpayer_type: str | None = None,
) -> str:
    if not knowledge_base_ids:
        raise ValueError("至少选择一个知识库")
    date_number = int(query_date.strftime("%Y%m%d"))
    regions = ["全国"] if region == "全国" else ["全国", region]
    policy_conditions = [
        'policy_status == "active"',
        f"region in [{', '.join(_quote(item) for item in regions)}]",
        f"effective_start <= {date_number}",
        f"(effective_end == 0 or effective_end >= {date_number})",
    ]
    if tax_type:
        policy_conditions.append(f"tax_type == {_quote(tax_type)}")
    if taxpayer_type:
        policy_conditions.append(f"taxpayer_type == {_quote(taxpayer_type)}")
    knowledge_bases = ", ".join(str(value) for value in sorted(set(knowledge_base_ids)))
    return (
        f"owner_id == {owner_id} and knowledge_base_id in [{knowledge_bases}] and "
        f"(policy_status == \"internal\" or ({' and '.join(policy_conditions)}))"
    )
