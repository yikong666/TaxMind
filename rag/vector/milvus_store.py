"""TaxMind Milvus Collection 与批量入库。"""

# Collection 同时维护 Dense 与 Sparse 索引，并保存可过滤政策元数据。
from dataclasses import dataclass
from typing import Protocol

from pymilvus import AnnSearchRequest, DataType, MilvusClient, WeightedRanker


@dataclass(frozen=True)
class VectorRecord:
    id: str
    child_id: int
    parent_id: int
    document_id: int
    knowledge_base_id: int
    owner_id: int
    text: str
    parent_content: str
    dense_vector: list[float]
    sparse_vector: dict[int, float]
    metadata: dict[str, str | int]


@dataclass(frozen=True)
class SearchHit:
    id: str
    hybrid_score: float
    rerank_score: float | None
    child_id: int
    parent_id: int
    document_id: int
    text: str
    parent_content: str
    metadata: dict[str, str | int]


class VectorStore(Protocol):
    def replace_document(self, document_id: int, records: list[VectorRecord]) -> None: ...

    def hybrid_search(
        self,
        dense: list[float],
        sparse: dict[int, float],
        filter_expression: str,
        top_k: int,
        candidate_k: int,
    ) -> list[SearchHit]: ...


class MilvusVectorStore:
    def __init__(self, uri: str, database: str, collection: str, dense_dim: int):
        bootstrap = MilvusClient(uri=uri)
        if database not in bootstrap.list_databases():
            bootstrap.create_database(database)
        bootstrap.close()
        self.client = MilvusClient(uri=uri, db_name=database)
        self.collection = collection
        self.dense_dim = dense_dim
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        if self.client.has_collection(self.collection):
            self.client.load_collection(self.collection)
            return
        schema = self.client.create_schema(auto_id=False, enable_dynamic_field=True)
        schema.add_field("id", DataType.VARCHAR, is_primary=True, max_length=100)
        schema.add_field("child_id", DataType.INT64)
        schema.add_field("parent_id", DataType.INT64)
        schema.add_field("document_id", DataType.INT64)
        schema.add_field("knowledge_base_id", DataType.INT64)
        schema.add_field("owner_id", DataType.INT64)
        schema.add_field("text", DataType.VARCHAR, max_length=65535)
        schema.add_field("parent_content", DataType.VARCHAR, max_length=65535)
        schema.add_field("dense_vector", DataType.FLOAT_VECTOR, dim=self.dense_dim)
        schema.add_field("sparse_vector", DataType.SPARSE_FLOAT_VECTOR)
        indexes = self.client.prepare_index_params()
        indexes.add_index(
            "dense_vector", index_name="dense_index", index_type="AUTOINDEX", metric_type="IP"
        )
        indexes.add_index(
            "sparse_vector",
            index_name="sparse_index",
            index_type="SPARSE_INVERTED_INDEX",
            metric_type="IP",
        )
        self.client.create_collection(self.collection, schema=schema, index_params=indexes)
        self.client.load_collection(self.collection)

    def replace_document(self, document_id: int, records: list[VectorRecord]) -> None:
        self.client.delete(self.collection, filter=f"document_id == {document_id}")
        self.client.flush(self.collection)
        if records:
            self.client.upsert(
                self.collection,
                data=[
                    {
                        "id": item.id,
                        "child_id": item.child_id,
                        "parent_id": item.parent_id,
                        "document_id": item.document_id,
                        "knowledge_base_id": item.knowledge_base_id,
                        "owner_id": item.owner_id,
                        "text": item.text,
                        "parent_content": item.parent_content,
                        "dense_vector": item.dense_vector,
                        "sparse_vector": item.sparse_vector,
                        **item.metadata,
                    }
                    for item in records
                ],
            )
            self.client.flush(self.collection)

    def hybrid_search(
        self,
        dense: list[float],
        sparse: dict[int, float],
        filter_expression: str,
        top_k: int,
        candidate_k: int,
    ) -> list[SearchHit]:
        requests = [
            AnnSearchRequest(
                [dense],
                "dense_vector",
                {"metric_type": "IP", "params": {}},
                limit=candidate_k,
                expr=filter_expression,
            ),
            AnnSearchRequest(
                [sparse],
                "sparse_vector",
                {"metric_type": "IP", "params": {}},
                limit=candidate_k,
                expr=filter_expression,
            ),
        ]
        output_fields = [
            "child_id", "parent_id", "document_id", "text", "parent_content",
            "region", "doc_no", "tax_type", "taxpayer_type", "effective_start",
            "effective_end", "policy_status", "source_url",
        ]
        result = self.client.hybrid_search(
            self.collection,
            requests,
            WeightedRanker(0.6, 0.4),
            limit=top_k,
            output_fields=output_fields,
        )[0]
        return [
            SearchHit(
                id=str(hit["id"]),
                hybrid_score=float(hit["distance"]),
                rerank_score=None,
                child_id=int(hit["entity"]["child_id"]),
                parent_id=int(hit["entity"]["parent_id"]),
                document_id=int(hit["entity"]["document_id"]),
                text=str(hit["entity"]["text"]),
                parent_content=str(hit["entity"]["parent_content"]),
                metadata={field: hit["entity"].get(field, "") for field in output_fields[5:]},
            )
            for hit in result
        ]
