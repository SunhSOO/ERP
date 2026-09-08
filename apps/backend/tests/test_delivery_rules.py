"""Rules the delivery module must not let the UI bypass."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_low_confidence_clause_cannot_reach_the_wbs(client: TestClient) -> None:
    """The screen labels these 검토 필요. The API has to make that label true."""

    response = client.post("/api/v1/clauses/cls-5-3/promote-to-task")

    assert response.status_code == 409
    assert response.json()["code"] == "STATE_CONFLICT"

    tasks = client.get("/api/v1/projects/prj-daon/tasks").json()["data"]
    assert all(task["title"] != '"운영 안정화 지원" 범위 산정' for task in tasks)


def test_high_confidence_clause_becomes_a_task(client: TestClient) -> None:
    response = client.post("/api/v1/clauses/cls-6/promote-to-task")

    assert response.status_code == 200
    created = response.json()["data"]
    assert created["title"] == "월간 진행 보고서 제출"
    assert created["status"] == "planned"


def test_a_clause_cannot_be_promoted_twice(client: TestClient) -> None:
    client.post("/api/v1/clauses/cls-6/promote-to-task")
    second = client.post("/api/v1/clauses/cls-6/promote-to-task")

    assert second.status_code == 409


def test_shift_preview_does_not_move_anything(client: TestClient) -> None:
    """The confirm dialog calls this. It must be read-only."""

    before = client.get("/api/v1/projects/prj-daon/milestones").json()["data"]

    preview = client.post(
        "/api/v1/milestones/ms-m3/shift", json={"new_end": "2026-09-19", "dry_run": True}
    )

    assert preview.status_code == 200
    assert preview.json()["data"], "후행 업무가 있어야 미리보기가 의미를 가진다"
    after = client.get("/api/v1/projects/prj-daon/milestones").json()["data"]
    assert before == after


def test_applying_a_shift_moves_the_previewed_tasks(client: TestClient) -> None:
    """Preview and apply must agree; the dialog quotes the preview to the user."""

    previewed = client.post(
        "/api/v1/milestones/ms-m3/shift", json={"new_end": "2026-09-19", "dry_run": True}
    ).json()["data"]

    applied = client.post(
        "/api/v1/milestones/ms-m3/shift", json={"new_end": "2026-09-19", "dry_run": False}
    ).json()["data"]

    assert applied == previewed

    tasks = {task["code"]: task for task in client.get(
        "/api/v1/projects/prj-daon/tasks"
    ).json()["data"]}
    for shift in previewed:
        assert tasks[shift["task_code"]]["end"] == shift["new_end"]


def test_blocked_task_states_why_and_who(client: TestClient) -> None:
    tasks = client.get("/api/v1/projects/prj-daon/tasks").json()["data"]
    blocked = [task for task in tasks if task["status"] == "blocked"]

    assert blocked
    for task in blocked:
        assert task["blocked_reason"]
        assert task["blocked_owner"]
