"""专项评测指标测试正常命中、排名和空数据边界。"""

from rag.evaluation.metrics import evaluate_records


def test_evaluation_metrics_include_retrieval_and_tax_accuracy() -> None:
    summary = evaluate_records(
        [
            {
                "expected_doc_nos": ["A"],
                "retrieved_doc_nos": ["X", "A"],
                "actual_doc_no": "A",
                "expected_region": "全国",
                "actual_region": "全国",
                "period_valid": True,
                "expected_risk": "LOW",
                "actual_risk": "LOW",
            }
        ],
        k=2,
    )
    assert summary.recall_at_k == 1
    assert summary.precision_at_k == 0.5
    assert summary.mrr == 0.5
    assert summary.doc_no_accuracy == 1


def test_evaluation_empty_records_returns_zeroes() -> None:
    assert evaluate_records([]).hit_rate == 0
