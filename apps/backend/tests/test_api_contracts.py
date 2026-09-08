"""The response envelope and error contract from 05_API_AND_EVENT_CONTRACTS.md."""

from __future__ import annotations

from typing import Any


def test_single_resource_is_wrapped_with_a_trace_id(
    client: Any, project: dict[str, Any]
) -> None:
    response = client.get(f"/api/v1/projects/{project['id']}")

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"data", "meta"}
    assert body["data"]["code"] == "TEST-1"
    assert body["meta"]["trace_id"]


def test_collection_carries_pagination_meta(client: Any, project: dict[str, Any]) -> None:
    body = client.get("/api/v1/projects").json()

    assert isinstance(body["data"], list)
    assert body["meta"]["total"] == len(body["data"])
    assert body["meta"]["has_more"] is False


def test_missing_resource_returns_problem_details(
    client: Any, signed_up: dict[str, str]
) -> None:
    response = client.get("/api/v1/projects/does-not-exist")

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["code"] == "NOT_FOUND"
    assert body["type"].endswith("/not-found")
    assert body["instance"] == "/api/v1/projects/does-not-exist"
    # 사용자가 화면에서 읽는 값이 응답 헤더와 같아야 한다.
    assert body["trace_id"] == response.headers["x-trace-id"]


def test_unauthenticated_request_returns_problem_details(client: Any) -> None:
    response = client.get("/api/v1/projects")

    assert response.status_code == 401
    body = response.json()
    assert body["code"] == "AUTHENTICATION_REQUIRED"
    assert body["trace_id"] == response.headers["x-trace-id"]


def test_validation_failure_lists_the_offending_fields(
    client: Any, signed_up: dict[str, str]
) -> None:
    response = client.post("/api/v1/projects", json={"name": ""})

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "VALIDATION_FAILED"
    assert body.get("errors") or body.get("detail")


def test_every_response_carries_a_trace_header(client: Any) -> None:
    assert client.get("/health/live").headers["x-trace-id"]
