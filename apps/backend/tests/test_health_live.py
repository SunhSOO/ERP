from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from lep.bootstrap.app import app


def test_health_live_returns_minimal_liveness_payload_and_trace_header() -> None:
    client = TestClient(app)

    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "lep-api"}
    assert response.headers["x-trace-id"]


def test_health_live_reuses_a_valid_request_id_for_traceability() -> None:
    client = TestClient(app)

    response = client.get("/health/live", headers={"X-Request-ID": "request-001"})

    assert response.status_code == 200
    assert response.headers["x-trace-id"] == "request-001"


def test_ready_reports_each_dependency(client: Any) -> None:
    """컨테이너가 떴다는 것과 쓸 수 있다는 것은 다르다.

    이름 있는 도커 볼륨이 root 소유로 만들어지면 폴더는 있고 쓰기만 막힌다.
    그 상태를 첫 업로드가 아니라 여기서 드러낸다.
    """

    body = client.get("/health/ready").json()

    assert body["status"] == "ok"
    assert {c["name"] for c in body["checks"]} == {"database", "vault", "uploads"}
    assert all(c["ok"] for c in body["checks"]), body


def test_ready_names_the_directory_it_cannot_write_to(
    client: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # 파일을 디렉터리 자리에 두면 그 아래에는 아무것도 쓸 수 없다.
    blocked = tmp_path / "blocked"
    blocked.write_text("나는 디렉터리가 아니다", encoding="utf-8")
    monkeypatch.setenv("LEP_UPLOAD_DIR", str(blocked))

    body = client.get("/health/ready").json()

    assert body["status"] == "degraded"
    uploads = next(c for c in body["checks"] if c["name"] == "uploads")
    assert uploads["ok"] is False
    assert str(blocked) in uploads["detail"]
