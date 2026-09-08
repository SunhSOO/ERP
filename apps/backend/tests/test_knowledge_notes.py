"""Vault notes, which is what the 회의록 and 지식 볼트 screens read.

회의록은 별도 저장소를 갖지 않는다. 프로젝트 볼트의 ``meetings`` 폴더에 있는
노트가 곧 회의록이다. 화면이 그 규칙에 기대므로 여기서 고정한다.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def _create_note(client: Any, project_id: str, **body: Any) -> dict[str, Any]:
    response = client.post(f"/api/v1/projects/{project_id}/notes", json=body)
    assert response.status_code == 201, response.text
    return dict(response.json()["data"])


def test_a_note_written_to_the_meetings_folder_reads_back_as_a_meeting(
    client: Any, project: dict[str, Any]
) -> None:
    note = _create_note(
        client,
        project["id"],
        title="2026-09-08 착수 회의",
        body="참석: 김서준\n\n- 킥오프",
        folder="meetings",
    )

    assert note["source"] == "meeting"
    assert note["title"] == "2026-09-08 착수 회의"

    listed = client.get(f"/api/v1/projects/{project['id']}/notes").json()["data"]
    meetings = [n for n in listed if n["source"] == "meeting"]
    assert [n["title"] for n in meetings] == ["2026-09-08 착수 회의"]


def test_a_note_in_the_default_folder_is_not_a_meeting(
    client: Any, project: dict[str, Any]
) -> None:
    note = _create_note(client, project["id"], title="메모", body="아무거나")

    assert note["source"] == "manual"


def test_a_note_lands_in_its_own_project_vault(
    client: Any, project: dict[str, Any], env: Path
) -> None:
    _create_note(client, project["id"], title="회의", body="본문", folder="meetings")

    other = client.post(
        "/api/v1/projects", json={"name": "다른 프로젝트", "code": "OTHER-1"}
    ).json()["data"]

    # 파일이 자기 프로젝트 폴더 아래에만 있어야 한다.
    vault = env / "vault"
    assert (vault / project["code"] / "meetings" / "회의.md").is_file()
    assert not (vault / other["code"] / "meetings" / "회의.md").exists()

    # 그리고 다른 프로젝트의 화면에 새어 나오지 않아야 한다.
    listed = client.get(f"/api/v1/projects/{other['id']}/notes").json()["data"]
    assert "회의" not in {n["title"] for n in listed}


def test_wikilinks_become_backlinks(client: Any, project: dict[str, Any]) -> None:
    _create_note(client, project["id"], title="설계 결정", body="본문", folder="notes")
    _create_note(
        client,
        project["id"],
        title="2026-09-08 회의",
        body="[[설계 결정]]을 따른다.",
        folder="meetings",
    )

    listed = client.get(f"/api/v1/projects/{project['id']}/notes").json()["data"]
    target = next(n for n in listed if n["title"] == "설계 결정")

    assert [b["label"] for b in target["backlinks"]] == ["2026-09-08 회의"]


def test_writing_a_note_requires_a_session(client: Any, project: dict[str, Any]) -> None:
    client.post("/api/v1/auth/logout")

    response = client.post(
        f"/api/v1/projects/{project['id']}/notes", json={"title": "몰래", "body": ""}
    )

    assert response.status_code == 401
    assert response.json()["code"] == "AUTHENTICATION_REQUIRED"
