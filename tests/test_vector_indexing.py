# 向量化测试使用确定性向量替身验证状态回写和失败恢复。
from fastapi.testclient import TestClient

from rag.embedding.bge_m3 import BgeM3EmbeddingProvider, HybridEmbedding
from tests.test_document_processing import upload_document
from tests.test_knowledge_bases import authenticate


class FakeEmbedding:
    def embed(self, texts: list[str]) -> list[HybridEmbedding]:
        return [HybridEmbedding([1.0, 0.0, 0.0], {index + 1: 0.5}) for index, _ in enumerate(texts)]


class MemoryVectorStore:
    def __init__(self) -> None:
        self.documents: dict[int, list] = {}

    def replace_document(self, document_id: int, records: list) -> None:
        self.documents[document_id] = records


class FailingVectorStore:
    def replace_document(self, document_id: int, records: list) -> None:
        raise ConnectionError("Milvus unavailable")


def create_internal_document(client: TestClient) -> tuple[dict[str, str], int]:
    headers = authenticate(client)
    knowledge_base = client.post(
        "/api/v1/knowledge-bases",
        headers=headers,
        json={"name": "内部资料", "description": "办税流程", "kb_type": "internal"},
    ).json()["data"]
    document_id = upload_document(
        client,
        headers,
        knowledge_base["id"],
        "guide.md",
        "# 申报流程\n登录系统后填写申报表。".encode(),
        "text/markdown",
    )
    client.post(f"/api/v1/documents/{document_id}/parse", headers=headers, json={})
    return headers, document_id


def test_document_is_indexed_with_dense_sparse_and_parent_metadata(
    client: TestClient, monkeypatch
) -> None:
    headers, document_id = create_internal_document(client)
    store = MemoryVectorStore()
    monkeypatch.setattr("backend.api.v1.documents.get_embedding_provider", lambda: FakeEmbedding())
    monkeypatch.setattr("backend.api.v1.documents.get_vector_store", lambda: store)

    response = client.post(f"/api/v1/documents/{document_id}/index", headers=headers)

    assert response.status_code == 200
    assert response.json()["data"]["indexed_count"] == 1
    record = store.documents[document_id][0]
    assert record.sparse_vector == {1: 0.5}
    assert "申报表" in record.parent_content
    assert record.metadata["original_name"] == "guide.md"
    chunks = client.get(f"/api/v1/documents/{document_id}/chunks", headers=headers).json()
    assert chunks["data"][0]["children"][0]["vector_status"] == "indexed"


def test_index_failure_marks_chunks_failed(client: TestClient, monkeypatch) -> None:
    headers, document_id = create_internal_document(client)
    monkeypatch.setattr("backend.api.v1.documents.get_embedding_provider", lambda: FakeEmbedding())
    monkeypatch.setattr("backend.api.v1.documents.get_vector_store", lambda: FailingVectorStore())

    response = client.post(f"/api/v1/documents/{document_id}/index", headers=headers)

    assert response.status_code == 500
    assert response.json()["code"] == "VECTOR_INDEX_FAILED"
    chunks = client.get(f"/api/v1/documents/{document_id}/chunks", headers=headers).json()
    assert chunks["data"][0]["children"][0]["vector_status"] == "failed"


def test_sparse_row_is_normalized_to_python_values() -> None:
    class SparseRow:
        col = [7, 11]
        data = [0.25, 0.75]

    assert BgeM3EmbeddingProvider._sparse_row(SparseRow()) == {7: 0.25, 11: 0.75}
