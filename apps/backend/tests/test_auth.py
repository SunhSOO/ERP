"""회원가입과 로그인.

첫 계정이 관리자가 되는 규칙과, 인증 없이는 아무것도 볼 수 없다는 규칙을 고정한다.
"""

from __future__ import annotations

from typing import Any


def test_first_account_becomes_the_administrator(client: Any) -> None:
    body = client.post(
        "/api/v1/auth/signup",
        json={"email": "first@example.invalid", "display_name": "첫 사용자",
              "password": "correct-horse-battery"},
    ).json()["data"]

    assert body["role"] == "admin"


def test_second_account_is_an_ordinary_member(client: Any) -> None:
    client.post(
        "/api/v1/auth/signup",
        json={"email": "first@example.invalid", "display_name": "첫 사용자",
              "password": "correct-horse-battery"},
    )
    client.cookies.clear()

    body = client.post(
        "/api/v1/auth/signup",
        json={"email": "second@example.invalid", "display_name": "둘째",
              "password": "correct-horse-battery"},
    ).json()["data"]

    assert body["role"] == "member"


def test_signup_state_tells_the_screen_whether_this_is_the_first_account(
    client: Any,
) -> None:
    before = client.get("/api/v1/auth/signup-state").json()["data"]
    assert before["first_account"] is True

    client.post(
        "/api/v1/auth/signup",
        json={"email": "first@example.invalid", "display_name": "첫 사용자",
              "password": "correct-horse-battery"},
    )

    after = client.get("/api/v1/auth/signup-state").json()["data"]
    assert after["first_account"] is False


def test_short_password_is_refused(client: Any) -> None:
    response = client.post(
        "/api/v1/auth/signup",
        json={"email": "a@example.invalid", "display_name": "짧은", "password": "short"},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_FAILED"


def test_duplicate_email_is_refused(client: Any, signed_up: dict[str, str]) -> None:
    client.cookies.clear()
    response = client.post(
        "/api/v1/auth/signup",
        json={"email": "PM@Example.invalid", "display_name": "다른 이름",
              "password": "correct-horse-battery"},
    )

    assert response.status_code == 409
    assert "이미 가입" in response.json()["detail"]


def test_login_and_logout_round_trip(client: Any, signed_up: dict[str, str]) -> None:
    client.post("/api/v1/auth/logout")
    assert client.get("/api/v1/auth/me").status_code == 401

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "pm@example.invalid", "password": "correct-horse-battery"},
    )
    assert login.status_code == 200
    assert client.get("/api/v1/auth/me").json()["data"]["email"] == "pm@example.invalid"


def test_wrong_password_does_not_reveal_whether_the_account_exists(
    client: Any, signed_up: dict[str, str]
) -> None:
    """없는 계정과 틀린 비밀번호가 같은 응답을 낸다."""

    client.cookies.clear()
    missing = client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.invalid", "password": "correct-horse-battery"},
    )
    wrong = client.post(
        "/api/v1/auth/login",
        json={"email": "pm@example.invalid", "password": "wrong-password-here"},
    )

    assert missing.status_code == wrong.status_code == 422
    assert missing.json()["detail"] == wrong.json()["detail"]


def test_session_cookie_is_httponly(client: Any) -> None:
    response = client.post(
        "/api/v1/auth/signup",
        json={"email": "a@example.invalid", "display_name": "가",
              "password": "correct-horse-battery"},
    )

    header = response.headers["set-cookie"]
    assert "httponly" in header.lower()
    assert "samesite=lax" in header.lower()


def test_every_business_endpoint_requires_a_session(client: Any) -> None:
    for path in ("/api/v1/projects", "/api/v1/auth/me"):
        assert client.get(path).status_code == 401, path
