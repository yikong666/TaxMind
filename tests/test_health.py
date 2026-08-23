# 健康检查必须维持统一响应结构，供部署探活稳定调用。
from fastapi.testclient import TestClient


def test_health_check_returns_standard_response(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "code": "OK",
        "message": "操作成功",
        "data": {"status": "healthy", "version": "0.1.0"},
    }
