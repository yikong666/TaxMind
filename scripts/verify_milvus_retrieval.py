"""使用合成向量验证 Milvus 时效与地区过滤，运行后自动清理。"""
from dataclasses import replace
from datetime import date

from backend.core.config import get_settings
from rag.embedding.bge_m3 import BgeM3EmbeddingProvider
from rag.retrieval.filters import build_metadata_filter
from rag.vector.milvus_store import MilvusVectorStore, VectorRecord

TEST_DOCUMENT_ID = 990001


def record(vector_id: str, region: str, status: str, start: int, end: int) -> VectorRecord:
    return VectorRecord(
        id=vector_id,
        child_id=len(vector_id),
        parent_id=len(vector_id),
        document_id=TEST_DOCUMENT_ID,
        knowledge_base_id=99,
        owner_id=88,
        text=vector_id,
        parent_content=f"{vector_id} parent",
        dense_vector=[1.0] + [0.0] * 1023,
        sparse_vector={1: 1.0},
        metadata={
            "region": region,
            "doc_no": vector_id,
            "tax_type": "增值税",
            "taxpayer_type": "小规模纳税人",
            "effective_start": start,
            "effective_end": end,
            "policy_status": status,
            "source_url": "https://www.chinatax.gov.cn/",
        },
    )


def main() -> None:
    settings = get_settings()
    store = MilvusVectorStore(
        f"http://{settings.milvus_host}:{settings.milvus_port}",
        settings.milvus_database,
        settings.milvus_collection,
        settings.embedding_dense_dim,
    )
    records = [
        record("active-national", "全国", "active", 20250101, 0),
        record("active-chongqing", "重庆", "active", 20250101, 20261231),
        record("expired-status", "重庆", "expired", 20250101, 20261231),
        record("replaced-status", "重庆", "replaced", 20250101, 20261231),
        record("expired-period", "重庆", "active", 20250101, 20251231),
        record("future-policy", "重庆", "active", 20270101, 0),
        record("active-sichuan", "四川", "active", 20250101, 0),
        record("internal-document", "", "internal", 0, 0),
    ]
    embedding = BgeM3EmbeddingProvider(settings.embedding_model_path, settings.embedding_device)
    vectors = embedding.embed([item.text for item in records] + ["重庆增值税优惠政策"])
    records = [
        replace(item, dense_vector=vector.dense, sparse_vector=vector.sparse)
        for item, vector in zip(records, vectors[:-1], strict=True)
    ]
    query_vector = vectors[-1]
    try:
        store.replace_document(TEST_DOCUMENT_ID, records)
        expression = build_metadata_filter(
            owner_id=88,
            knowledge_base_ids=[99],
            query_date=date(2026, 8, 23),
            region="重庆",
        )
        hits = store.hybrid_search(
            query_vector.dense,
            query_vector.sparse,
            expression,
            top_k=20,
            candidate_k=20,
        )
        actual = {hit.id for hit in hits}
        expected = {"active-national", "active-chongqing", "internal-document"}
        if actual != expected:
            raise AssertionError(f"过滤结果错误：expected={expected}, actual={actual}")
        print(f"Milvus P0 过滤验证通过：{sorted(actual)}")
    finally:
        store.replace_document(TEST_DOCUMENT_ID, [])


if __name__ == "__main__":
    main()
