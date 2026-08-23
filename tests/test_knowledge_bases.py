# 知识库测试覆盖租户隔离、批量上传和对象存储清理。
from fastapi.testclient import TestClient


def authenticate(client: TestClient, username: str = "kb_user") -> dict[str, str]:
    client.captcha_store.values["register-captcha"] = "A7K9"  # type: ignore[attr-defined]
    register = client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "password": "SecurePass123!",
            "confirm_password": "SecurePass123!",
            "captcha_id": "register-captcha",
            "captcha_code": "A7K9",
        },
    )
    assert register.status_code == 201
    client.captcha_store.values["login-captcha"] = "B8M4"  # type: ignore[attr-defined]
    login = client.post(
        "/api/v1/auth/login",
        json={
            "username": username,
            "password": "SecurePass123!",
            "captcha_id": "login-captcha",
            "captcha_code": "B8M4",
        },
    )
    return {"Authorization": f"Bearer {login.json()['data']['access_token']}"}


def create_knowledge_base(client: TestClient, headers: dict[str, str], name: str = "全国政策库"):
    return client.post(
        "/api/v1/knowledge-bases",
        headers=headers,
        json={"name": name, "description": "国家税收政策", "kb_type": "public_policy"},
    )


def test_knowledge_base_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/knowledge-bases")
    assert response.status_code == 401
    assert response.json()["code"] == "NOT_AUTHENTICATED"


def test_create_list_update_and_get_knowledge_base(client: TestClient) -> None:
    headers = authenticate(client)
    created = create_knowledge_base(client, headers)
    assert created.status_code == 201
    knowledge_base_id = created.json()["data"]["id"]

    listed = client.get("/api/v1/knowledge-bases", headers=headers)
    assert listed.json()["data"][0]["document_count"] == 0
    assert listed.json()["data"][0]["chunk_count"] == 0

    updated = client.patch(
        f"/api/v1/knowledge-bases/{knowledge_base_id}",
        headers=headers,
        json={"name": "全国通用政策库", "description": "已更新"},
    )
    assert updated.json()["data"]["name"] == "全国通用政策库"

    detail = client.get(f"/api/v1/knowledge-bases/{knowledge_base_id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["data"]["documents"] == []


def test_knowledge_base_detail_exposes_document_status_and_chunk_statistics(
    client: TestClient,
) -> None:
    headers = authenticate(client, "kb_statistics")
    knowledge_base_id = create_knowledge_base(client, headers).json()["data"]["id"]
    uploaded = client.post(
        f"/api/v1/knowledge-bases/{knowledge_base_id}/documents",
        headers=headers,
        files={"files": ("policy.md", "# 政策\n有效内容".encode(), "text/markdown")},
    ).json()["data"][0]
    client.post(f"/api/v1/documents/{uploaded['id']}/parse", headers=headers, json={})

    listed = client.get("/api/v1/knowledge-bases", headers=headers).json()["data"][0]
    detail = client.get(
        f"/api/v1/knowledge-bases/{knowledge_base_id}", headers=headers
    ).json()["data"]
    assert listed["document_count"] == 1
    assert listed["chunk_count"] == 1
    assert detail["documents"][0]["parse_status"] == "completed"
    assert detail["documents"][0]["policy_metadata"]["is_complete"] is False


def test_duplicate_knowledge_base_name_is_rejected(client: TestClient) -> None:
    headers = authenticate(client)
    assert create_knowledge_base(client, headers).status_code == 201
    response = create_knowledge_base(client, headers)
    assert response.status_code == 409
    assert response.json()["code"] == "KNOWLEDGE_BASE_EXISTS"


def test_upload_multiple_documents_to_private_storage(client: TestClient) -> None:
    headers = authenticate(client)
    knowledge_base_id = create_knowledge_base(client, headers).json()["data"]["id"]
    response = client.post(
        f"/api/v1/knowledge-bases/{knowledge_base_id}/documents",
        headers=headers,
        files=[
            ("files", ("policy.md", "# 增值税政策".encode(), "text/markdown")),
            ("files", ("guide.pdf", b"%PDF-test", "application/pdf")),
        ],
    )

    assert response.status_code == 201
    assert len(response.json()["data"]) == 2
    assert all(item["parse_status"] == "pending" for item in response.json()["data"])
    assert len(client.object_storage.objects) == 2  # type: ignore[attr-defined]


def test_upload_rejects_unsupported_or_empty_files(client: TestClient) -> None:
    headers = authenticate(client)
    knowledge_base_id = create_knowledge_base(client, headers).json()["data"]["id"]

    unsupported = client.post(
        f"/api/v1/knowledge-bases/{knowledge_base_id}/documents",
        headers=headers,
        files={"files": ("danger.exe", b"binary", "application/octet-stream")},
    )
    empty = client.post(
        f"/api/v1/knowledge-bases/{knowledge_base_id}/documents",
        headers=headers,
        files={"files": ("empty.pdf", b"", "application/pdf")},
    )
    assert unsupported.status_code == 400
    assert unsupported.json()["code"] == "UNSUPPORTED_FILE_TYPE"
    assert empty.status_code == 400
    assert empty.json()["code"] == "EMPTY_FILE"


def test_users_cannot_access_each_others_knowledge_bases(client: TestClient) -> None:
    first_headers = authenticate(client, "first_user")
    knowledge_base_id = create_knowledge_base(client, first_headers).json()["data"]["id"]
    second_headers = authenticate(client, "second_user")

    response = client.get(
        f"/api/v1/knowledge-bases/{knowledge_base_id}", headers=second_headers
    )
    assert response.status_code == 404


def test_delete_knowledge_base_removes_stored_documents(client: TestClient) -> None:
    headers = authenticate(client)
    knowledge_base_id = create_knowledge_base(client, headers).json()["data"]["id"]
    client.post(
        f"/api/v1/knowledge-bases/{knowledge_base_id}/documents",
        headers=headers,
        files={"files": ("policy.md", b"policy", "text/markdown")},
    )
    response = client.delete(f"/api/v1/knowledge-bases/{knowledge_base_id}", headers=headers)

    assert response.status_code == 200
    assert client.object_storage.objects == {}  # type: ignore[attr-defined]
