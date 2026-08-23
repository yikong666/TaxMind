"""Chunk 编辑删除、向量失效、重新索引与租户隔离测试。"""

from fastapi.testclient import TestClient

from tests.test_knowledge_bases import authenticate
from tests.test_vector_indexing import FakeEmbedding, MemoryVectorStore, create_internal_document


class CleanupFailingStore:
    def replace_document(self, document_id: int, records: list) -> None:
        raise ConnectionError("Milvus unavailable")


# 向量组件使用内存替身，精确断言修改前后 Milvus 文档记录的替换行为。
def setup_vectors(monkeypatch, store):
    monkeypatch.setattr("backend.api.v1.documents.get_embedding_provider", lambda: FakeEmbedding())
    monkeypatch.setattr("backend.api.v1.documents.get_vector_store", lambda: store)


def chunks(client: TestClient, headers: dict[str, str], document_id: int):
    return client.get(f"/api/v1/documents/{document_id}/chunks", headers=headers).json()["data"]


def test_parent_edit_invalidates_vectors_and_reindex_uses_new_parent_content(
    client: TestClient, monkeypatch
) -> None:
    headers, document_id = create_internal_document(client)
    store = MemoryVectorStore()
    setup_vectors(monkeypatch, store)
    assert client.post(f"/api/v1/documents/{document_id}/index", headers=headers).status_code == 200
    parent_id = chunks(client, headers, document_id)[0]["id"]

    updated = client.patch(
        f"/api/v1/chunks/parents/{parent_id}",
        headers=headers,
        json={"heading": "新版申报流程", "content": "新版系统中填写并复核申报表。"},
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["heading"] == "新版申报流程"
    assert store.documents[document_id] == []
    summary = client.get(f"/api/v1/documents/{document_id}/vector-status", headers=headers).json()[
        "data"
    ]
    assert summary == {
        "document_id": document_id,
        "total": 1,
        "pending": 1,
        "indexed": 0,
        "failed": 0,
        "needs_reindex": True,
        "can_index": True,
    }

    reindexed = client.post(f"/api/v1/documents/{document_id}/index", headers=headers)
    assert reindexed.json()["data"]["indexed_count"] == 1
    assert store.documents[document_id][0].parent_content == "新版系统中填写并复核申报表。"


def test_child_edit_and_delete_update_status_and_counts(client: TestClient, monkeypatch) -> None:
    headers, document_id = create_internal_document(client)
    store = MemoryVectorStore()
    setup_vectors(monkeypatch, store)
    child_id = chunks(client, headers, document_id)[0]["children"][0]["id"]

    updated = client.patch(
        f"/api/v1/chunks/children/{child_id}",
        headers=headers,
        json={"content": "人工修订后的申报检索文本。"},
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["content"] == "人工修订后的申报检索文本。"
    assert updated.json()["data"]["vector_status"] == "pending"

    deleted = client.delete(f"/api/v1/chunks/children/{child_id}", headers=headers)
    assert deleted.status_code == 200
    summary = client.get(f"/api/v1/documents/{document_id}/vector-status", headers=headers).json()[
        "data"
    ]
    assert summary["total"] == 0
    assert summary["can_index"] is False
    cannot_index = client.post(f"/api/v1/documents/{document_id}/index", headers=headers)
    assert cannot_index.status_code == 400
    assert cannot_index.json()["code"] == "DOCUMENT_HAS_NO_CHUNKS"


def test_parent_delete_updates_document_counts(client: TestClient, monkeypatch) -> None:
    headers, document_id = create_internal_document(client)
    store = MemoryVectorStore()
    setup_vectors(monkeypatch, store)
    parent_id = chunks(client, headers, document_id)[0]["id"]
    assert client.delete(f"/api/v1/chunks/parents/{parent_id}", headers=headers).status_code == 200
    assert chunks(client, headers, document_id) == []
    summary = client.get(f"/api/v1/documents/{document_id}/vector-status", headers=headers).json()[
        "data"
    ]
    assert summary["total"] == 0


def test_cleanup_failure_keeps_chunk_unchanged(client: TestClient, monkeypatch) -> None:
    headers, document_id = create_internal_document(client)
    original = chunks(client, headers, document_id)[0]
    setup_vectors(monkeypatch, CleanupFailingStore())
    response = client.patch(
        f"/api/v1/chunks/parents/{original['id']}",
        headers=headers,
        json={"content": "不应保存的正文"},
    )
    assert response.status_code == 500
    assert response.json()["code"] == "VECTOR_CLEANUP_FAILED"
    assert chunks(client, headers, document_id)[0]["content"] == original["content"]


def test_chunk_operations_are_isolated_by_owner(client: TestClient, monkeypatch) -> None:
    first, document_id = create_internal_document(client)
    parent_id = chunks(client, first, document_id)[0]["id"]
    second = authenticate(client, "other_chunk_owner")
    setup_vectors(monkeypatch, MemoryVectorStore())
    assert (
        client.patch(
            f"/api/v1/chunks/parents/{parent_id}",
            headers=second,
            json={"heading": "越权修改"},
        ).status_code
        == 404
    )
    assert (
        client.get(f"/api/v1/documents/{document_id}/vector-status", headers=second).status_code
        == 404
    )
