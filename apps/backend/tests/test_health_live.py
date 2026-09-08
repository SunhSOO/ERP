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
