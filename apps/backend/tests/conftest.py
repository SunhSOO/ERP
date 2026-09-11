"""Shared test fixtures.

Each test gets a fresh SQLite database and a fresh vault directory, so nothing
carries between tests and no test can pass because a previous one left data
behind. SQLite stands in for PostgreSQL: every column type used is portable, and
timestamps are normalised on read (``common.db.as_utc``), which is the one place
the two databases differ in a way the code notices.

Every import of application code is deferred into a fixture body. Importing the
FastAPI app at conftest scope would configure logging before pytest has finished
installing its output capture, and the resulting handler outlives the stream it
was given.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the application at throwaway storage."""

    monkeypatch.setenv("LEP_DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setenv("LEP_OBSIDIAN_VAULT", str(tmp_path / "vault"))
    monkeypatch.setenv("LEP_UPLOAD_DIR", str(tmp_path / "uploads"))
    # 어댑터는 전부 기본값(픽스처/빈 값)으로 둔다. 테스트가 외부를 부르지 않는다.
    for name in ("VCS", "VAULT", "MAIL", "CONVERTER", "LLM"):
        monkeypatch.delenv(f"LEP_ADAPTER_{name}", raising=False)
    return tmp_path


@pytest.fixture
def client(env: Path) -> Iterator[Any]:
    """A TestClient over a fresh app with an empty database."""

    from fastapi.testclient import TestClient

    import lep.common.db as db_module
    from lep.bootstrap.app import create_app
    from lep.common.schema import create_all

    # 엔진은 프로세스 전역이라 테스트마다 다시 만들어야 한다.
    db_module._engine = None
    db_module._session_factory = None

    # knowledge 모듈의 볼트는 lru_cache로 잡혀 있다. 새 경로를 쓰도록 비운다.
    from lep.modules.knowledge.public import get_vault
    from lep.modules.mail.public import get_mail_service

    get_vault.cache_clear()
    get_mail_service.cache_clear()

    create_all()

    # 라이프사이클을 켜지 않는다. 여기서 정리되지 않아 인터프리터를 데려간다.
    yield TestClient(create_app())

    db_module._engine = None
    db_module._session_factory = None


@pytest.fixture
def signed_up(client: Any) -> dict[str, str]:
    """가입한 첫 사용자. 세션 쿠키가 클라이언트에 남는다."""

    response = client.post(
        "/api/v1/auth/signup",
        json={
            "email": "pm@example.invalid",
            "display_name": "김서준",
            "password": "correct-horse-battery",
        },
    )
    assert response.status_code == 201, response.text
    return dict(response.json()["data"])


@pytest.fixture
def admin_user(client: Any) -> dict[str, str]:
    """첫 가입자는 관리자다. 클라이언트에 관리자의 세션 쿠키를 설정한다."""

    # Make admin_user the first user (so they become admin)
    response = client.post(
        "/api/v1/auth/signup",
        json={
            "email": "admin@example.invalid",
            "display_name": "관리자",
            "password": "correct-horse-battery",
        },
    )
    assert response.status_code == 201, response.text
    return dict(response.json()["data"])


@pytest.fixture
def project(client: Any, signed_up: dict[str, str]) -> dict[str, Any]:
    """로그인한 사용자가 만든 프로젝트 하나."""

    response = client.post(
        "/api/v1/projects",
        json={"name": "테스트 프로젝트", "code": "TEST-1", "customer_name": "고객사"},
    )
    assert response.status_code == 201, response.text
    return dict(response.json()["data"])


@pytest.fixture
def other_user(client: Any, signed_up: dict[str, str]) -> dict[str, str]:
    """두 번째 가입자는 일반 사용자다."""

    response = client.post(
        "/api/v1/auth/signup",
        json={
            "email": "other@example.invalid",
            "display_name": "다른 사용자",
            "password": "correct-horse-battery",
        },
    )
    assert response.status_code == 201, response.text
    return dict(response.json()["data"])


@pytest.fixture
def disabled_user(client: Any) -> dict[str, str]:
    """비활성화된 사용자."""

    from lep.common.db import get_session
    from lep.modules.iam.infrastructure.models import UserRow

    # Sign up the user
    response = client.post(
        "/api/v1/auth/signup",
        json={
            "email": "disabled@example.invalid",
            "display_name": "비활성 사용자",
            "password": "correct-horse-battery",
        },
    )
    assert response.status_code == 201, response.text
    user_data = dict(response.json()["data"])

    # Disable the user
    db = next(get_session())
    try:
        user = db.query(UserRow).filter(UserRow.id == user_data["id"]).one()
        user.status = "suspended"
        db.commit()
    finally:
        db.close()

    return user_data
