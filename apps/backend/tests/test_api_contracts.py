"""The response envelope and error contract from 05_API_AND_EVENT_CONTRACTS.md."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_single_resource_is_wrapped_with_a_trace_id(client: TestClient) -> None:
    response = client.get("/api/v1/projects/prj-daon")

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"data", "meta"}
    assert body["data"]["code"] == "PRJ-2026-001"
    assert body["meta"]["trace_id"]


def test_collection_carries_pagination_meta(client: TestClient) -> None:
    response = client.get("/api/v1/projects")

    body = response.json()
    assert isinstance(body["data"], list)
    assert body["meta"]["total"] == len(body["data"])
    assert body["meta"]["has_more"] is False


def test_missing_resource_returns_problem_details(client: TestClient) -> None:
    response = client.get("/api/v1/projects/does-not-exist")

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["code"] == "NOT_FOUND"
    assert body["type"].endswith("/not-found")
    assert body["instance"] == "/api/v1/projects/does-not-exist"
    # The user reads this ID on screen; it has to match the response header.
    assert body["trace_id"] == response.headers["x-trace-id"]


def test_validation_failure_lists_the_offending_fields(client: TestClient) -> None:
    response = client.post(
        "/api/v1/milestones/ms-m3/shift", json={"new_end": "not-a-date"}
    )

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "VALIDATION_FAILED"
    assert any("new_end" in error["field"] for error in body["errors"])
