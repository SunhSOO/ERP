"""Contract tests for the real integration adapters.

None of these call an external service. ``AGENTS.md`` 14절 forbids tests that
reach real systems, so the GitHub adapter is driven with recorded response
shapes, the Obsidian adapter with a temporary vault on disk, and the Hiworks
adapter with constructed email messages.
"""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime
from email.message import EmailMessage, Message
from pathlib import Path

import pytest

from lep.common.adapters import AdapterKind, _select
from lep.modules.delivery.infrastructure.statement_parser import split_clauses
from lep.modules.documents.infrastructure.kordoc_converter import (
    DEFAULT_PRESET,
    PRESETS,
    KordocConverter,
)
from lep.modules.integrations.infrastructure.github_vcs import (
    GitHubVcsAdapter,
    RepoActivity,
    extract_codes,
)
from lep.modules.knowledge.domain.entities import NoteSource
from lep.modules.knowledge.infrastructure.obsidian_vault import ObsidianVault
from lep.modules.mail.infrastructure.hiworks_imap import HiworksMailAdapter, decode

# ── 어댑터 선택 ──────────────────────────────────────────────────────────


def test_default_is_always_the_fixture(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LEP_ADAPTER_VCS", raising=False)

    assert _select("LEP_ADAPTER_VCS", "github", {}).kind is AdapterKind.FIXTURE


def test_incomplete_configuration_does_not_silently_pretend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """반쯤 설정된 실제 어댑터는 왜 쓰이지 않는지 말해야 한다.

    조용히 픽스처로 넘어가면 화면이 깃허브에 붙은 척하게 된다.
    """

    monkeypatch.setenv("LEP_ADAPTER_VCS", "github")

    choice = _select("LEP_ADAPTER_VCS", "github", {"LEP_GITHUB_TOKEN": None})

    assert choice.kind is AdapterKind.FIXTURE
    assert choice.unavailable_reason is not None
    assert "LEP_GITHUB_TOKEN" in choice.unavailable_reason


# ── kordoc ───────────────────────────────────────────────────────────────


def test_screen_template_maps_to_a_kordoc_preset() -> None:
    assert PRESETS["표준 검수보고서"] == "보고서"


def test_unknown_template_falls_back_to_the_report_preset() -> None:
    assert PRESETS.get("존재하지 않는 양식", DEFAULT_PRESET) == "보고서"


def test_empty_markdown_is_refused_without_running_anything(tmp_path: Path) -> None:
    converter = KordocConverter(cli_path="does-not-exist", output_dir=str(tmp_path))

    succeeded, detail = converter.convert("   \n  ", template="보고서")

    assert succeeded is False
    assert detail == "빈 문서는 변환할 수 없습니다."


def test_missing_converter_is_reported_not_swallowed(tmp_path: Path) -> None:
    converter = KordocConverter(
        cli_path=str(tmp_path / "nope.js"), output_dir=str(tmp_path / "out")
    )

    succeeded, detail = converter.convert("# 제목\n", template="보고서")

    assert succeeded is False
    assert detail


# ── 과업지시서 조항 분리 ──────────────────────────────────────────────────


def test_korean_articles_become_clauses() -> None:
    clauses = split_clauses(
        "제1조 (목적) 이 과업의 목적은 다음과 같다.\n"
        "제3조 2항 WMS 연동 인터페이스를 정의한다.\n"
    )

    assert [c.article for c in clauses] == ["제1조", "제3조 2항"]


def test_article_body_spanning_several_lines_is_joined() -> None:
    clauses = split_clauses("제2조 첫 줄\n이어지는 줄\n제3조 다른 조항입니다\n")

    assert clauses[0].text == "첫 줄 이어지는 줄"


def test_outline_form_is_used_when_there_are_no_articles() -> None:
    clauses = split_clauses("1. 요구사항 정의를 수행한다.\n2. 설계 문서를 제출한다.\n")

    assert [c.article for c in clauses] == ["1.", "2."]


def test_plain_prose_yields_no_clauses() -> None:
    """조항이 없으면 없다고 한다. 문단을 쪼개 조항인 척하지 않는다."""

    assert split_clauses("그냥 줄글입니다. 조항 번호가 없습니다.\n") == []


# ── 깃허브 ───────────────────────────────────────────────────────────────


def test_task_codes_are_found_in_titles_and_branch_names() -> None:
    codes = extract_codes(
        "feat: WBS 정합 (TSK-1038)", "feature/WP-PLT-001-repository-bootstrap"
    )

    assert codes == {"TSK-1038", "WP-PLT-001"}


def test_unrelated_text_yields_no_codes() -> None:
    assert extract_codes("chore: import approved ERP design baseline") == set()


def _activity(**overrides: object) -> RepoActivity:
    base: dict[str, object] = {
        "open_pull_requests": 0,
        "pull_requests": [],
        "branches": [],
        "commits": [],
        "issues": [],
        "pushed_at": datetime(2026, 9, 7, tzinfo=UTC),
    }
    base.update(overrides)
    return RepoActivity(**base)  # type: ignore[arg-type]


def _adapter() -> GitHubVcsAdapter:
    return GitHubVcsAdapter(token="not-a-real-token", repos={"*": "owner/repo"})


def test_repository_work_with_no_wbs_task_is_undefined_work() -> None:
    status, mismatches, mappings = _adapter().reconcile(
        "p1",
        "owner/repo",
        _activity(
            open_pull_requests=1,
            pull_requests=[("PR #221", "배포 파이프라인 개선", "open", False, set())],
        ),
        [("TSK-1038", "IF 정의서 v2", "blocked")],
    )

    assert [item.kind.value for item in mismatches] == ["undefined_work"]
    assert mappings[0].task_code is None
    assert status.health.value == "mismatch"


def test_done_task_with_an_open_pull_request_is_a_status_conflict() -> None:
    _status, mismatches, mappings = _adapter().reconcile(
        "p1",
        "owner/repo",
        _activity(
            pull_requests=[("PR #218", "TSK-1050 성능 테스트", "open", False, {"TSK-1050"})]
        ),
        [("TSK-1050", "API 게이트웨이 성능 테스트", "done")],
    )

    assert [item.kind.value for item in mismatches] == ["status_conflict"]
    assert mappings[0].aligned is False


def test_merged_pull_request_for_a_done_task_is_aligned() -> None:
    _status, mismatches, mappings = _adapter().reconcile(
        "p1",
        "owner/repo",
        _activity(
            pull_requests=[("PR #218", "TSK-1050 성능 테스트", "closed", True, {"TSK-1050"})]
        ),
        [("TSK-1050", "API 게이트웨이 성능 테스트", "done")],
    )

    assert mismatches == []
    assert mappings[0].aligned is True


def test_a_repository_with_nothing_linked_is_not_reported_as_healthy() -> None:
    """0% 정합률 옆에 "정상"이 붙으면 사용자가 모순을 스스로 풀어야 한다."""

    status, mismatches, mappings = _adapter().reconcile(
        "p1",
        "owner/repo",
        _activity(branches=[("main", set())], default_branch="main"),
        [("TSK-1038", "IF 정의서 v2", "blocked")],
    )

    assert mismatches == []
    assert mappings == []
    assert status.match_rate_percent == 0
    assert status.health.value == "stale"


def test_branches_carrying_a_task_code_count_as_linked_work() -> None:
    status, _mismatches, mappings = _adapter().reconcile(
        "p1",
        "owner/repo",
        _activity(
            branches=[("main", set()), ("feature/TSK-1042-scenarios", {"TSK-1042"})],
            default_branch="main",
        ),
        [("TSK-1042", "검수 시나리오 작성", "in_progress")],
    )

    assert mappings[0].vcs_ref == "브랜치 feature/TSK-1042-scenarios"
    assert status.match_rate_percent == 100
    assert status.health.value == "ok"


def test_default_branch_is_never_reported_as_a_deviation() -> None:
    """main에서 일어나는 일은 계획 그 자체다. 이탈로 보고하면 소음만 는다."""

    _status, mismatches, mappings = _adapter().reconcile(
        "p1",
        "owner/repo",
        _activity(branches=[("main", {"WP-PLT-001"})], default_branch="main"),
        [("TSK-1038", "IF 정의서 v2", "blocked")],
    )

    assert mismatches == []
    assert mappings == []


def test_coded_branch_missing_from_the_wbs_is_undefined_work() -> None:
    _status, mismatches, mappings = _adapter().reconcile(
        "p1",
        "owner/repo",
        _activity(
            branches=[("main", set()), ("feature/WP-PLT-001-bootstrap", {"WP-PLT-001"})],
            default_branch="main",
        ),
        [("TSK-1038", "IF 정의서 v2", "blocked")],
    )

    assert [item.kind.value for item in mismatches] == ["undefined_work"]
    assert "WP-PLT-001" in mismatches[0].detail
    assert mappings[0].vcs_ref == "브랜치 feature/WP-PLT-001-bootstrap"


def test_branch_without_any_code_is_left_alone() -> None:
    """코드가 없는 브랜치는 버려지는 실험인 경우가 많다."""

    _status, mismatches, mappings = _adapter().reconcile(
        "p1",
        "owner/repo",
        _activity(branches=[("scratch", set())], default_branch="main"),
        [("TSK-1038", "IF 정의서 v2", "blocked")],
    )

    assert mismatches == []
    assert mappings == []


# ── 옵시디언 볼트 ────────────────────────────────────────────────────────

CODE = "TEST-1"


def _vault(tmp_path: Path) -> ObsidianVault:
    """프로젝트 폴더 하나를 갖춘 볼트."""

    vault = ObsidianVault(root=tmp_path)
    base = vault.ensure(CODE)
    (base / ".obsidian").mkdir(exist_ok=True)
    (base / ".obsidian" / "app.json").write_text("{}", encoding="utf-8")
    (base / "MTG-088.md").write_text(
        "# 검수 일정 리뷰\n관련: [[TSK-1038]]\n", encoding="utf-8"
    )
    (base / "TSK-1038.md").write_text(
        "## TSK-1038 인터페이스 정의서\n상태: #미확정\n", encoding="utf-8"
    )
    (base / "meetings" / "kickoff.md").write_text(
        "킥오프. [[TSK-1038]] 논의.\n", encoding="utf-8"
    )
    return vault


def test_ensure_creates_the_project_folder_with_starter_directories(tmp_path: Path) -> None:
    base = ObsidianVault(root=tmp_path).ensure("GWANGJU")

    assert base.is_dir()
    assert (base / "README.md").is_file()
    assert (base / "meetings").is_dir()


def test_ensure_does_not_overwrite_an_existing_readme(tmp_path: Path) -> None:
    """볼트는 사용자의 것이다. 두 번 불러도 사람이 쓴 내용을 덮지 않는다."""

    vault = ObsidianVault(root=tmp_path)
    readme = vault.ensure(CODE) / "README.md"
    readme.write_text("사람이 쓴 내용", encoding="utf-8")

    vault.ensure(CODE)

    assert readme.read_text(encoding="utf-8") == "사람이 쓴 내용"


def test_vault_reads_markdown_files_and_skips_obsidian_internals(tmp_path: Path) -> None:
    notes = _vault(tmp_path).list_notes("p1", CODE)

    assert {n.title for n in notes} == {"README", "MTG-088", "TSK-1038", "kickoff"}


def test_wikilinks_become_backlinks_on_the_target_note(tmp_path: Path) -> None:
    notes = {n.title: n for n in _vault(tmp_path).list_notes("p1", CODE)}

    assert {b.label for b in notes["TSK-1038"].backlinks} == {"MTG-088", "kickoff"}


def test_folder_name_decides_the_note_source(tmp_path: Path) -> None:
    notes = {n.title: n for n in _vault(tmp_path).list_notes("p1", CODE)}

    assert notes["kickoff"].source is NoteSource.MEETING
    assert notes["MTG-088"].source is NoteSource.MANUAL


def test_unresolved_tag_surfaces_as_a_warning(tmp_path: Path) -> None:
    notes = {n.title: n for n in _vault(tmp_path).list_notes("p1", CODE)}

    assert notes["TSK-1038"].warning == "미확정 태그"


def test_task_code_is_extracted_from_note_content(tmp_path: Path) -> None:
    notes = {n.title: n for n in _vault(tmp_path).list_notes("p1", CODE)}

    assert notes["TSK-1038"].task_code == "TSK-1038"


def test_status_reports_the_real_path_and_count(tmp_path: Path) -> None:
    status = _vault(tmp_path).status("p1", CODE)

    assert status.note_count == 4
    assert status.vault_path == str(tmp_path / CODE)


def test_missing_project_folder_is_reported_as_failed(tmp_path: Path) -> None:
    status = ObsidianVault(root=tmp_path).status("p1", "ABSENT")

    assert status.health.value == "failed"
    assert status.note_count == 0


def test_creating_a_note_writes_a_file_obsidian_can_open(tmp_path: Path) -> None:
    vault = _vault(tmp_path)

    vault.create_note(CODE, title="필드 매핑 표 회신", body="출처: 메일\n", folder="inbox")

    written = tmp_path / CODE / "inbox" / "필드 매핑 표 회신.md"
    assert written.is_file()
    assert "메일" in written.read_text(encoding="utf-8")


def test_creating_a_note_never_overwrites_existing_text(tmp_path: Path) -> None:
    """같은 이름이 있으면 덮지 않고 옆에 쓴다."""

    vault = _vault(tmp_path)
    original = (tmp_path / CODE / "TSK-1038.md").read_text(encoding="utf-8")

    vault.create_note(CODE, title="TSK-1038", body="새 내용\n", folder=".")

    assert (tmp_path / CODE / "TSK-1038.md").read_text(encoding="utf-8") == original


# ── 하이웍스 메일 ────────────────────────────────────────────────────────


def _hiworks() -> HiworksMailAdapter:
    return HiworksMailAdapter(
        host="imap.invalid",
        port=993,
        user="pm@example.invalid",
        password="not-a-real-password",
        domains={"daon-corp.example": "prj-daon"},
    )


def _raw_mail(subject: str, sender: str, body: str) -> Message:
    message = EmailMessage()
    message["Message-ID"] = "<mail-001@example.invalid>"
    message["From"] = sender
    message["Subject"] = subject
    message["Date"] = "Mon, 07 Sep 2026 14:20:00 +0900"
    message.set_content(body)
    return message


def test_korean_subject_headers_are_decoded() -> None:
    """하이웍스 한글 제목은 RFC 2047로 인코딩돼 온다."""

    assert decode("=?UTF-8?B?7ZWc6riAIOygnOuqqQ==?=") == "한글 제목"


def test_sender_domain_decides_the_project() -> None:
    parsed = _hiworks()._to_message(
        _raw_mail("자료 공유", "이서영 <lee@daon-corp.example>", "첨부드립니다.")
    )

    assert parsed is not None
    assert parsed.project_id == "prj-daon"
    assert parsed.sender_org == "daon-corp.example"


def test_unknown_domain_is_marked_unrelated() -> None:
    parsed = _hiworks()._to_message(
        _raw_mail("정기 점검 안내", "총무팀 <admin@other.invalid>", "안내드립니다.")
    )

    assert parsed is not None
    assert parsed.project_id is None
    assert parsed.classification.value == "unrelated"


def test_schedule_wording_is_detected_but_never_claimed_as_certain() -> None:
    """키워드 규칙은 모델이 아니다. 신뢰도를 높게 매기면 화면이 거짓을 말한다."""

    parsed = _hiworks()._to_message(
        _raw_mail(
            "M3 검수 일정 관련",
            "이서영 <lee@daon-corp.example>",
            "일정 변경을 요청드립니다. 1주 연기 부탁드립니다.",
        )
    )

    assert parsed is not None
    assert parsed.intent == "일정 변경"
    assert parsed.confidence is not None
    assert parsed.confidence.value == "low"
    assert parsed.milestone_code == "M3"


def test_message_without_an_id_is_skipped() -> None:
    message = EmailMessage()
    message["From"] = "lee@daon-corp.example"
    message["Subject"] = "제목"

    assert _hiworks()._to_message(message) is None


def test_workflow_state_is_kept_as_an_overlay_not_written_to_the_server() -> None:
    """메일함은 사용자의 것이다. 처리 표시를 서버에 쓰지 않는다."""

    adapter = _hiworks()
    original = adapter._to_message(
        _raw_mail("자료 공유", "이서영 <lee@daon-corp.example>", "첨부드립니다.")
    )
    assert original is not None

    adapter.replace_message(dataclasses.replace(original, handled=True, note_id="note-1"))

    assert adapter._with_overlay(original).handled is True
    assert adapter._with_overlay(original).note_id == "note-1"
