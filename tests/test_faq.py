from fastapi.testclient import TestClient

from tests.test_knowledge_bases import authenticate

# 内存缓存记录版本号，模拟 Redis 精确命中和写操作失效行为。


class MemoryFaqCache:
    def __init__(self) -> None:
        self.versions: dict[int, int] = {}
        self.values: dict[tuple[int, int, str, str], dict] = {}

    def get(self, owner_id: int, region: str, query: str) -> dict | None:
        return self.values.get((owner_id, self.versions.get(owner_id, 0), region, query))

    def set(self, owner_id: int, region: str, query: str, value: dict, ttl_seconds: int) -> None:
        self.values[(owner_id, self.versions.get(owner_id, 0), region, query)] = value.copy()

    def invalidate(self, owner_id: int) -> None:
        self.versions[owner_id] = self.versions.get(owner_id, 0) + 1


def setup_cache(monkeypatch) -> MemoryFaqCache:
    cache = MemoryFaqCache()
    monkeypatch.setattr("backend.api.v1.faqs.get_faq_cache", lambda: cache)
    return cache


def create_faq(
    client: TestClient,
    headers: dict[str, str],
    *,
    question: str = "小规模纳税人如何申报增值税？",
    region: str = "全国",
    is_enabled: bool = True,
    effective_start: str | None = "2026-01-01",
    effective_end: str | None = "2026-12-31",
):
    return client.post(
        "/api/v1/faqs",
        headers=headers,
        json={
            "question": question,
            "answer": "登录电子税务局后，进入增值税申报模块办理。",
            "category": "申报",
            "region": region,
            "doc_no": "税总发〔2026〕1号",
            "effective_start": effective_start,
            "effective_end": effective_end,
            "is_enabled": is_enabled,
        },
    )


def test_faq_crud_and_duplicate_question(client: TestClient, monkeypatch) -> None:
    setup_cache(monkeypatch)
    headers = authenticate(client)
    created = create_faq(client, headers)
    assert created.status_code == 201
    faq_id = created.json()["data"]["id"]

    duplicate = create_faq(client, headers, question=" 小规模纳税人如何申报增值税？！ ")
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "FAQ_EXISTS"

    updated = client.patch(
        f"/api/v1/faqs/{faq_id}", headers=headers, json={"is_enabled": False}
    )
    assert updated.json()["data"]["is_enabled"] is False
    assert len(client.get("/api/v1/faqs", headers=headers).json()["data"]) == 1
    assert client.delete(f"/api/v1/faqs/{faq_id}", headers=headers).status_code == 200
    assert client.get(f"/api/v1/faqs/{faq_id}", headers=headers).status_code == 404


def test_faq_is_isolated_by_owner(client: TestClient, monkeypatch) -> None:
    setup_cache(monkeypatch)
    first_headers = authenticate(client, "faq_owner_one")
    faq_id = create_faq(client, first_headers).json()["data"]["id"]
    second_headers = authenticate(client, "faq_owner_two")
    assert client.get(f"/api/v1/faqs/{faq_id}", headers=second_headers).status_code == 404


def test_exact_faq_hit_is_cached_then_invalidated(client: TestClient, monkeypatch) -> None:
    cache = setup_cache(monkeypatch)
    headers = authenticate(client)
    faq_id = create_faq(client, headers).json()["data"]["id"]
    payload = {
        "query": "小规模纳税人如何申报增值税？",
        "region": "重庆",
        "query_date": "2026-08-23",
    }
    first = client.post("/api/v1/faqs/route/match", headers=headers, json=payload).json()["data"]
    second = client.post("/api/v1/faqs/route/match", headers=headers, json=payload).json()["data"]
    assert first["source"] == "mysql_bm25"
    assert first["continue_to_rag"] is False
    assert second["source"] == "redis"

    next_year = client.post(
        "/api/v1/faqs/route/match",
        headers=headers,
        json={**payload, "query_date": "2027-01-01"},
    ).json()["data"]
    assert next_year["matched"] is False

    version_before = next(iter(cache.versions.values()))
    client.patch(f"/api/v1/faqs/{faq_id}", headers=headers, json={"is_enabled": False})
    assert next(iter(cache.versions.values())) > version_before
    after_disable = client.post(
        "/api/v1/faqs/route/match", headers=headers, json=payload
    ).json()["data"]
    assert after_disable["matched"] is False
    assert after_disable["continue_to_rag"] is True


def test_bm25_low_score_continues_to_rag(client: TestClient, monkeypatch) -> None:
    setup_cache(monkeypatch)
    headers = authenticate(client)
    create_faq(client, headers)
    result = client.post(
        "/api/v1/faqs/route/match",
        headers=headers,
        json={"query": "个人所得税专项附加扣除", "region": "全国"},
    ).json()["data"]
    assert result["matched"] is False
    assert result["source"] == "rag"


def test_expired_disabled_and_other_region_faqs_do_not_match(
    client: TestClient, monkeypatch
) -> None:
    setup_cache(monkeypatch)
    headers = authenticate(client)
    create_faq(
        client,
        headers,
        question="重庆发票如何申领？",
        region="重庆",
        effective_end="2025-12-31",
    )
    create_faq(
        client,
        headers,
        question="四川发票如何申领？",
        region="四川",
    )
    create_faq(
        client,
        headers,
        question="全国发票如何申领？",
        is_enabled=False,
    )
    result = client.post(
        "/api/v1/faqs/route/match",
        headers=headers,
        json={"query": "重庆发票如何申领？", "region": "重庆", "query_date": "2026-08-23"},
    ).json()["data"]
    assert result["matched"] is False


def test_national_faq_can_match_local_query_but_local_cannot_cross_region(
    client: TestClient, monkeypatch
) -> None:
    setup_cache(monkeypatch)
    headers = authenticate(client)
    create_faq(client, headers, question="发票丢失如何处理？", region="全国")
    local_result = client.post(
        "/api/v1/faqs/route/match",
        headers=headers,
        json={"query": "发票丢失如何处理？", "region": "重庆", "query_date": "2026-08-23"},
    ).json()["data"]
    assert local_result["matched"] is True

    create_faq(client, headers, question="重庆税务登记如何办理？", region="重庆")
    national_result = client.post(
        "/api/v1/faqs/route/match",
        headers=headers,
        json={"query": "重庆税务登记如何办理？", "region": "全国", "query_date": "2026-08-23"},
    ).json()["data"]
    assert national_result["matched"] is False
