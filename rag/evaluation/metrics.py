"""TaxMind 检索与财税专项离线评测指标。"""

from dataclasses import dataclass


@dataclass(slots=True)
class EvaluationSummary:
    recall_at_k: float
    precision_at_k: float
    mrr: float
    hit_rate: float
    doc_no_accuracy: float
    region_accuracy: float
    period_accuracy: float
    risk_accuracy: float


def evaluate_records(records: list[dict], k: int = 5) -> EvaluationSummary:
    """按文档编号相关性计算检索指标，并汇总领域字段准确率。"""
    if not records:
        return EvaluationSummary(*(0.0 for _ in range(8)))
    recalls, precisions, reciprocal_ranks, hits = [], [], [], []
    doc_ok = region_ok = period_ok = risk_ok = 0
    for record in records:
        expected = set(record.get("expected_doc_nos", []))
        retrieved = record.get("retrieved_doc_nos", [])[:k]
        relevant = sum(item in expected for item in retrieved)
        recalls.append(relevant / len(expected) if expected else 1.0)
        precisions.append(relevant / k)
        rank = next((index + 1 for index, item in enumerate(retrieved) if item in expected), 0)
        reciprocal_ranks.append(1 / rank if rank else 0.0)
        hits.append(float(bool(rank)))
        doc_ok += record.get("actual_doc_no") in expected
        region_ok += record.get("actual_region") == record.get("expected_region")
        period_ok += record.get("period_valid") is True
        risk_ok += record.get("actual_risk") == record.get("expected_risk")
    size = len(records)
    def mean(values: list[float]) -> float:
        return sum(values) / size
    return EvaluationSummary(
        mean(recalls),
        mean(precisions),
        mean(reciprocal_ranks),
        mean(hits),
        doc_ok / size,
        region_ok / size,
        period_ok / size,
        risk_ok / size,
    )
