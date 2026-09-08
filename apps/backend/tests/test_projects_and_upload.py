"""프로젝트 생성과 과업지시서 업로드.

시드 데이터가 없다는 것, 프로젝트마다 볼트가 생긴다는 것, 업로드가 조항으로
쪼개진다는 것을 고정한다.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def test_a_fresh_installation_has_no_projects(client: Any, signed_up: dict[str, str]) -> None:
    """"프로젝트는 아무것도 없이"가 실제로 지켜지는지."""

    body = client.get("/api/v1/projects").json()

    assert body["data"] == []
    assert body["meta"]["total"] == 0


def test_creating_a_project_makes_its_vault_folder(
    client: Any, env: Path, signed_up: dict[str, str]
) -> None:
    client.post("/api/v1/projects", json={"name": "광주 정수장", "code": "GWANGJU"})

    vault = env / "vault" / "GWANGJU"
    assert vault.is_dir()
    assert (vault / "README.md").is_file()
    # 옵시디언에서 바로 쓰도록 폴더를 미리 만들어 둔다.
    assert (vault / "meetings").is_dir()
    assert (vault / "statements").is_dir()


def test_each_project_gets_its_own_vault(
    client: Any, env: Path, signed_up: dict[str, str]
) -> None:
    """지식이 프로젝트 경계를 넘지 않는다."""

    client.post("/api/v1/projects", json={"name": "가", "code": "AAA"})
    second = client.post("/api/v1/projects", json={"name": "나", "code": "BBB"}).json()["data"]

    (env / "vault" / "AAA" / "notes").mkdir(parents=True, exist_ok=True)
    (env / "vault" / "AAA" / "notes" / "비밀.md").write_text("가 프로젝트 노트", encoding="utf-8")

    titles = {
        n["title"]
        for n in client.get(f"/api/v1/projects/{second['id']}/notes").json()["data"]
    }
    # 자기 README만 보이고 다른 프로젝트의 노트는 보이지 않는다.
    assert titles == {"README"}


def test_project_code_is_derived_when_omitted(client: Any, signed_up: dict[str, str]) -> None:
    body = client.post("/api/v1/projects", json={"name": "daon logistics"}).json()["data"]

    assert body["code"] == "DAON-LOGISTICS"


def test_a_code_that_would_escape_the_vault_directory_is_refused(
    client: Any, signed_up: dict[str, str]
) -> None:
    """코드는 폴더 이름이 된다. 경로 조작을 막는다."""

    response = client.post(
        "/api/v1/projects", json={"name": "나쁜 프로젝트", "code": "../../etc"}
    )

    assert response.status_code == 422


def test_duplicate_project_code_is_refused(client: Any, project: dict[str, Any]) -> None:
    response = client.post("/api/v1/projects", json={"name": "다른 이름", "code": "TEST-1"})

    assert response.status_code == 409


def test_a_new_project_has_no_progress_rather_than_zero_percent(
    client: Any, project: dict[str, Any]
) -> None:
    """0%는 "시작 안 함"이라는 뜻이다. 태스크가 없는 것과 다르다."""

    body = client.get(f"/api/v1/projects/{project['id']}/summary").json()["data"]

    assert body["wbs_progress_percent"] is None
    assert body["schedule_note"] == "아직 WBS가 없습니다"
    assert body["task_count"] == 0


def test_archived_projects_leave_the_list(client: Any, project: dict[str, Any]) -> None:
    client.post(f"/api/v1/projects/{project['id']}/archive")

    assert client.get("/api/v1/projects").json()["data"] == []


# ── 과업지시서 업로드 ──────────────────────────────────────────────────────

STATEMENT = """# 과업지시서

제1조 (목적) 이 과업은 물류 통합 플랫폼을 구축하는 것을 목적으로 한다.

제3조 2항 WMS 연동 인터페이스를 정의하고 문서로 제출한다.

제4조 1항 검수 시나리오를 작성하고 실행한다.
"""


def upload(client: Any, project_id: str, name: str, data: bytes) -> Any:
    return client.post(
        f"/api/v1/projects/{project_id}/statements",
        files={"file": (name, data, "application/octet-stream")},
    )


def test_uploading_a_markdown_statement_splits_it_into_clauses(
    client: Any, project: dict[str, Any]
) -> None:
    response = upload(client, project["id"], "과업지시서.md", STATEMENT.encode("utf-8"))

    assert response.status_code == 201, response.text
    body = response.json()["data"]
    assert body["analysed"] is True
    assert body["clause_count"] == 3
    # 분류는 로컬 LLM의 일이다. 지금 0이 정직하다.
    assert body["classified_count"] == 0

    clauses = client.get(f"/api/v1/statements/{body['id']}/clauses").json()["data"]
    assert [c["article"] for c in clauses] == ["제1조", "제3조 2항", "제4조 1항"]
    assert all(c["confidence"] == "low" for c in clauses)
    assert all(c["category"] == "미분류" for c in clauses)


def test_the_uploaded_original_is_kept_on_disk(
    client: Any, env: Path, project: dict[str, Any]
) -> None:
    upload(client, project["id"], "과업지시서.md", STATEMENT.encode("utf-8"))

    stored = list((env / "uploads" / "TEST-1").glob("*.md"))
    assert len(stored) == 1
    assert "제3조" in stored[0].read_text(encoding="utf-8")


def test_an_unsupported_format_is_refused_before_anything_is_written(
    client: Any, env: Path, project: dict[str, Any]
) -> None:
    response = upload(client, project["id"], "사진.png", b"\x89PNG\r\n")

    assert response.status_code == 422
    assert "지원하지 않는 형식" in response.json()["detail"]
    assert not (env / "uploads" / "TEST-1").exists()


def test_an_empty_file_is_refused(client: Any, project: dict[str, Any]) -> None:
    response = upload(client, project["id"], "빈.md", b"")

    assert response.status_code == 422


def test_a_document_with_no_articles_reports_zero_clauses_rather_than_inventing_them(
    client: Any, project: dict[str, Any]
) -> None:
    """조항이 없으면 없다고 말한다. 문단을 쪼개 조항인 척하지 않는다."""

    response = upload(client, project["id"], "잡문.md", "그냥 줄글입니다.\n".encode())

    body = response.json()["data"]
    assert body["clause_count"] == 0


def test_a_low_confidence_clause_cannot_reach_the_wbs(
    client: Any, project: dict[str, Any]
) -> None:
    """분류기가 없는 동안 모든 조항이 낮음이므로 자동 반영이 막힌다."""

    statement = upload(
        client, project["id"], "과업지시서.md", STATEMENT.encode("utf-8")
    ).json()["data"]
    clause = client.get(f"/api/v1/statements/{statement['id']}/clauses").json()["data"][0]

    response = client.post(f"/api/v1/clauses/{clause['id']}/promote-to-task")

    assert response.status_code == 409
    assert client.get(f"/api/v1/projects/{project['id']}/tasks").json()["data"] == []


def test_upload_requires_a_session(client: Any, project: dict[str, Any]) -> None:
    client.post("/api/v1/auth/logout")

    response = upload(client, project["id"], "과업지시서.md", STATEMENT.encode("utf-8"))

    assert response.status_code == 401


def test_the_upload_screen_can_ask_what_it_may_accept(
    client: Any, signed_up: dict[str, str]
) -> None:
    body = client.get("/api/v1/upload-limits").json()["data"]

    assert ".hwpx" in body["suffixes"]
    assert body["max_bytes"] > 0
