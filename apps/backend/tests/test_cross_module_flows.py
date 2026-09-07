"""Flows that cross module boundaries.

Each of these goes through the owning module's public interface. That is what
``scripts/check_boundaries.py`` protects, and these tests show the seams actually
work rather than just compiling.
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_promoting_mail_creates_a_vault_note(client: TestClient) -> None:
    before = client.get("/api/v1/projects/prj-daon/vault").json()["data"]["note_count"]

    response = client.post("/api/v1/mail/mail-002/promote-to-note")

    assert response.status_code == 200
    note_id = response.json()["data"]["note_id"]

    after = client.get("/api/v1/projects/prj-daon/vault").json()["data"]["note_count"]
    assert after == before + 1

    note = client.get(f"/api/v1/notes/{note_id}")
    assert note.status_code == 200
    assert note.json()["data"]["source"] == "mail"


def test_dismissing_mail_updates_the_home_card(client: TestClient) -> None:
    """The home card reads the count live from the mail module."""

    before = client.get("/api/v1/projects/prj-daon/summary").json()["data"][
        "unclassified_mail_count"
    ]
    assert before > 0

    client.post("/api/v1/mail/mail-001/dismiss")

    after = client.get("/api/v1/projects/prj-daon/summary").json()["data"][
        "unclassified_mail_count"
    ]
    assert after == before - 1


def test_mail_schedule_application_moves_the_milestone(client: TestClient) -> None:
    detail = client.get("/api/v1/mail/mail-001").json()["data"]
    assert detail["schedule_preview"], "일정 변경 메일은 영향 미리보기를 내야 한다"

    applied = client.post("/api/v1/mail/mail-001/apply-to-wbs")

    assert applied.status_code == 200
    assert applied.json()["data"] == detail["schedule_preview"]


def test_resolving_an_undefined_work_mismatch_registers_the_task(
    client: TestClient,
) -> None:
    """Screen 07's "새 WBS 태스크로 등록" goes through delivery's public interface."""

    tasks = {task["code"]: task for task in client.get(
        "/api/v1/projects/prj-daon/tasks"
    ).json()["data"]}
    assert tasks["TSK-1071"]["status"] == "vcs_only"

    response = client.post("/api/v1/vcs/mismatches/mis-221/resolve")

    assert response.status_code == 200
    assert response.json()["data"]["resolved"] is True

    tasks = {task["code"]: task for task in client.get(
        "/api/v1/projects/prj-daon/tasks"
    ).json()["data"]}
    assert tasks["TSK-1071"]["status"] == "planned"


def test_meeting_preview_matches_what_apply_does(client: TestClient) -> None:
    preview = client.get("/api/v1/meetings/mtg-088").json()["data"]["preview"]
    assert preview["milestone_code"] == "M3"
    assert preview["new_end"] == "2026-09-19"

    applied = client.post("/api/v1/meetings/mtg-088/apply", json={"mode": "wbs"})

    assert applied.status_code == 200
    assert applied.json()["data"]["shifts"] == preview["shifts"]


def test_meeting_can_be_applied_only_once(client: TestClient) -> None:
    client.post("/api/v1/meetings/mtg-088/apply", json={"mode": "vault_only"})
    second = client.post("/api/v1/meetings/mtg-088/apply", json={"mode": "wbs"})

    assert second.status_code == 409


def test_original_drive_documents_are_read_only(client: TestClient) -> None:
    categories = {
        item["category"]: item
        for item in client.get("/api/v1/projects/prj-daon/drive").json()["data"]
    }

    assert categories["original"]["read_only"] is True
    assert categories["deliverable"]["read_only"] is False


def test_failed_conversion_is_reported_not_hidden(client: TestClient) -> None:
    documents = {
        item["id"]: item
        for item in client.get("/api/v1/projects/prj-daon/documents").json()["data"]
    }
    failed = documents["doc-change-request"]

    assert failed["state"] == "failed"
    assert failed["failure_reason"]


def test_credentials_never_carry_secret_values(client: TestClient) -> None:
    """Screen 09 shows integration health. It must not carry tokens or paths."""

    credentials = client.get("/api/v1/projects/prj-daon/integrations").json()["data"]

    assert credentials
    for credential in credentials:
        assert set(credential) == {
            "kind",
            "label",
            "health",
            "detail",
            "missing_input",
        }
