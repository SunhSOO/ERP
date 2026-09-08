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


# ── 과업지시서 → 볼트 노트 ────────────────────────────────────────────────

STATEMENT = """1.과업의 개요

1.1과업명

O정수장 데이터 전처리 및 AI 개발 용역

1.2 과업 목적

ㅇ운영상태를 실시간으로 분석한다

2.과업수행 일반사항

2.1 보안사항

O산출물은 외부로 반출하지 않는다
"""


def _upload(client: Any, project: dict[str, Any], name: str = "과업지시서.md") -> dict[str, Any]:
    response = client.post(
        f"/api/v1/projects/{project['id']}/statements",
        files={"file": (name, STATEMENT.encode("utf-8"), "text/markdown")},
    )
    assert response.status_code == 201, response.text
    return dict(response.json()["data"])


def test_uploading_a_statement_writes_one_note_per_section(
    client: Any, project: dict[str, Any], env: Path
) -> None:
    """규칙으로 뽑은 절이 곧 볼트의 노트가 된다."""

    _upload(client, project)

    folder = env / "vault" / project["code"] / "statements" / "과업지시서"
    titles = {p.stem for p in folder.glob("*.md")}

    assert "과업지시서 1 과업의 개요" in titles
    assert "과업지시서 1.1 과업명" in titles
    assert "과업지시서 2.1 보안사항" in titles
    assert "과업지시서 목차" in titles


def test_a_section_note_links_to_its_parent(
    client: Any, project: dict[str, Any], env: Path
) -> None:
    """옵시디언의 백링크가 문서 구조를 그대로 보여 주어야 한다."""

    _upload(client, project)
    folder = env / "vault" / project["code"] / "statements" / "과업지시서"

    child = (folder / "과업지시서 1.1 과업명.md").read_text(encoding="utf-8")
    assert "상위: [[과업지시서 1 과업의 개요]]" in child

    parent = (folder / "과업지시서 1 과업의 개요.md").read_text(encoding="utf-8")
    assert "[[과업지시서 1.1 과업명]]" in parent
    assert "[[과업지시서 1.2 과업 목적]]" in parent


def test_the_section_body_reaches_the_note(
    client: Any, project: dict[str, Any], env: Path
) -> None:
    folder = env / "vault" / project["code"] / "statements" / "과업지시서"
    _upload(client, project)

    note = (folder / "과업지시서 2.1 보안사항.md").read_text(encoding="utf-8")
    assert "외부로 반출하지 않는다" in note


def test_the_notes_show_up_in_the_vault_listing(
    client: Any, project: dict[str, Any]
) -> None:
    """볼트 화면이 이 노트들을 읽을 수 있어야 한다."""

    _upload(client, project)

    notes = client.get(f"/api/v1/projects/{project['id']}/notes").json()["data"]
    statement_notes = [n for n in notes if n["source"] == "statement"]

    assert len(statement_notes) >= 5
    assert all(n["source"] == "statement" for n in statement_notes)


def test_reparsing_the_same_document_does_not_duplicate_notes(
    client: Any, project: dict[str, Any], env: Path
) -> None:
    """같은 문서를 다시 올려도 노트가 두 벌이 되지 않는다."""

    _upload(client, project)
    folder = env / "vault" / project["code"] / "statements" / "과업지시서"
    first = sorted(p.name for p in folder.glob("*.md"))

    _upload(client, project)

    assert sorted(p.name for p in folder.glob("*.md")) == first


def test_a_note_written_by_a_person_is_not_overwritten(
    client: Any, project: dict[str, Any], env: Path
) -> None:
    """볼트는 사용자의 것이다. 재파싱이 사람의 메모를 지우지 않는다."""

    folder = env / "vault" / project["code"] / "statements" / "과업지시서"
    folder.mkdir(parents=True, exist_ok=True)
    mine = folder / "과업지시서 1.1 과업명.md"
    mine.write_text("내가 직접 쓴 메모다.", encoding="utf-8")

    _upload(client, project)

    assert mine.read_text(encoding="utf-8") == "내가 직접 쓴 메모다."
    # 대신 옆에 자동 생성본이 생긴다. 조용히 버리지 않는다.
    assert (folder / "과업지시서 1.1 과업명 (자동).md").is_file()
