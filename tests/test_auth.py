# 认证测试覆盖验证码一次性消费、密码校验和重复用户名边界。
from fastapi.testclient import TestClient
from jose import jwt

from backend.core.config import get_settings


def add_captcha(client: TestClient, captcha_id: str = "captcha-1", code: str = "A7K9") -> None:
    client.captcha_store.values[captcha_id] = code  # type: ignore[attr-defined]


def registration_payload(**overrides: str) -> dict[str, str]:
    payload = {
        "username": "tax_user",
        "password": "SecurePass123!",
        "confirm_password": "SecurePass123!",
        "captcha_id": "captcha-1",
        "captcha_code": "A7K9",
    }
    payload.update(overrides)
    return payload


def test_captcha_endpoint_returns_svg_without_plaintext_code(client: TestClient) -> None:
    response = client.get("/api/v1/auth/captcha")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["captcha_id"]
    assert data["image_svg"].startswith("<svg")
    assert data["expires_in"] == 300


def test_register_and_login_success(client: TestClient) -> None:
    add_captcha(client)
    register_response = client.post("/api/v1/auth/register", json=registration_payload())

    assert register_response.status_code == 201
    assert register_response.json()["data"]["username"] == "tax_user"

    add_captcha(client, "captcha-2")
    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "username": "tax_user",
            "password": "SecurePass123!",
            "captcha_id": "captcha-2",
            "captcha_code": "A7K9",
        },
    )

    assert login_response.status_code == 200
    token_data = login_response.json()["data"]
    payload = jwt.decode(
        token_data["access_token"],
        get_settings().jwt_secret_key.get_secret_value(),
        algorithms=[get_settings().jwt_algorithm],
    )
    assert payload["sub"] == str(token_data["user"]["id"])
    assert token_data["token_type"] == "bearer"


def test_register_rejects_password_mismatch(client: TestClient) -> None:
    add_captcha(client)
    response = client.post(
        "/api/v1/auth/register",
        json=registration_payload(confirm_password="DifferentPass123!"),
    )

    assert response.status_code == 400
    assert response.json()["code"] == "PASSWORD_MISMATCH"


def test_register_rejects_duplicate_username(client: TestClient) -> None:
    add_captcha(client)
    assert client.post("/api/v1/auth/register", json=registration_payload()).status_code == 201
    add_captcha(client, "captcha-2")

    response = client.post(
        "/api/v1/auth/register",
        json=registration_payload(captcha_id="captcha-2"),
    )

    assert response.status_code == 409
    assert response.json()["code"] == "USERNAME_EXISTS"


def test_captcha_is_single_use(client: TestClient) -> None:
    add_captcha(client)
    first = client.post(
        "/api/v1/auth/register",
        json=registration_payload(captcha_code="WRONG"),
    )
    second = client.post("/api/v1/auth/register", json=registration_payload())

    assert first.status_code == 400
    assert second.status_code == 400
    assert second.json()["code"] == "INVALID_CAPTCHA"


def test_login_rejects_wrong_password(client: TestClient) -> None:
    add_captcha(client)
    client.post("/api/v1/auth/register", json=registration_payload())
    add_captcha(client, "captcha-2")

    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": "tax_user",
            "password": "WrongPassword!",
            "captcha_id": "captcha-2",
            "captcha_code": "A7K9",
        },
    )

    assert response.status_code == 401
    assert response.json()["code"] == "INVALID_CREDENTIALS"
