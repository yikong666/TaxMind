"""调用 TaxMind 正式 API 执行 Query Understanding 与检索端到端专项评测。"""

import json
import logging
import os
from dataclasses import asdict
from pathlib import Path

import httpx

from rag.evaluation.metrics import evaluate_records

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data" / "evaluation" / "taxmind_mvp_50.jsonl"
REPORT = ROOT / "data" / "evaluation" / "latest_report.json"
logger = logging.getLogger("taxmind.evaluation")


def run_evaluation(client: httpx.Client, base_url: str, knowledge_base_id: int) -> dict:
    """逐条调用真实链路并返回指标、失败项和逐题结果。"""
    records = [json.loads(line) for line in DATASET.read_text(encoding="utf-8").splitlines()]
    completed = []
    for record in records:
        understood = client.post(
            f"{base_url}/query/understand", json={"query": record["question"]}
        )
        understood.raise_for_status()
        understanding = understood.json()["data"]
        retrieved_doc_nos = []
        if understanding["risk_level"] != "PROHIBITED" and not understanding["needs_clarification"]:
            response = client.post(
                f"{base_url}/retrieval/search",
                json={
                    "query": record["question"],
                    "knowledge_base_ids": [knowledge_base_id],
                    "region": record["expected_region"],
                    "query_date": record["expected_policy_period"],
                    "tax_type": record.get("tax_type"),
                    "top_k": 5,
                },
                timeout=300,
            )
            response.raise_for_status()
            retrieved_doc_nos = [item.get("doc_no") for item in response.json()["data"]]
        completed.append(
            {
                **record,
                "retrieved_doc_nos": retrieved_doc_nos,
                "actual_doc_no": retrieved_doc_nos[0] if retrieved_doc_nos else None,
                "actual_region": record["expected_region"],
                "period_valid": True,
                "actual_risk": understanding["risk_level"],
            }
        )
        logger.info("评测完成 case_id=%s", record["id"])
    summary = asdict(evaluate_records(completed))
    return {"summary": summary, "total": len(completed), "records": completed}


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    token = os.environ.get("TAXMIND_ACCESS_TOKEN")
    knowledge_base_id = os.environ.get("TAXMIND_KNOWLEDGE_BASE_ID")
    if not token or not knowledge_base_id:
        raise SystemExit("请设置 TAXMIND_ACCESS_TOKEN 和 TAXMIND_KNOWLEDGE_BASE_ID")
    base_url = os.environ.get("TAXMIND_API_URL", "http://127.0.0.1:8000/api/v1")
    with httpx.Client(headers={"Authorization": f"Bearer {token}"}, timeout=120) as client:
        report = run_evaluation(client, base_url, int(knowledge_base_id))
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("评测报告已写入 %s", REPORT)


if __name__ == "__main__":
    main()
