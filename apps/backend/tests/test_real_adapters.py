"""Contract tests for the real integration adapters.

None of these call an external service. ``AGENTS.md`` 14절 forbids tests that
reach real systems, so the GitHub adapter is driven with recorded response
shapes and the Obsidian adapter with a temporary vault on disk.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from lep.common.adapters import AdapterKind, _select
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
from lep.modules.knowledge.domain.entities import Note, NoteSource
from lep.modules.knowledge.infrastructure.obsidian_vault import ObsidianVault

# ── 어댑터 선택 ──────────────────────────────────────────────────────────


def test_default_is_always_the_fixture(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LEP_ADAPTER_VCS", raising=False)

    assert _select("LEP_ADAPTER_VCS", "github", {}).kind is AdapterKind.FIXTURE


def test_incomplete_configuration_does_not_silently_pretend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A half-configured real adapter must say why it is not in use.

    Falling back quietly would let a screen claim it is talking to GitHub when
    it is reading fixtures.
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
    """A converter that will not start is a failure the screen must show."""

    converter = KordocConverter(
        cli_path=str(tmp_path / "nope.js"), output_dir=str(tmp_path / "out")
    )

    succeeded, detail = converter.convert("# 제목\n", template="보고서")

    assert succeeded is False
    assert detail


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
        "prj-daon",
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
        "prj-daon",
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
        "prj-daon",
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
        "prj-daon",
        "owner/repo",
        _activity(branches=[("main", set())]),
        [("TSK-1038", "IF 정의서 v2", "blocked")],
    )

    assert mismatches == []
    assert mappings == []
    assert status.match_rate_percent == 0
    assert status.health.value == "stale"


def test_branches_carrying_a_task_code_count_as_linked_work() -> None:
    status, _mismatches, mappings = _adapter().reconcile(
        "prj-daon",
        "owner/repo",
        _activity(branches=[("feature/TSK-1042-scenarios", {"TSK-1042"})]),
        [("TSK-1042", "검수 시나리오 작성", "in_progress")],
    )

    assert mappings[0].vcs_ref == "브랜치 feature/TSK-1042-scenarios"
    assert status.match_rate_percent == 100
    assert status.health.value == "ok"


# ── 옵시디언 볼트 ────────────────────────────────────────────────────────


def _vault(tmp_path: Path) -> ObsidianVault:
    (tmp_path / ".obsidian").mkdir()
    (tmp_path / ".obsidian" / "app.json").write_text("{}", encoding="utf-8")
    (tmp_path / "meetings").mkdir()
    (tmp_path / "MTG-088.md").write_text(
        "# 검수 일정 리뷰\n관련: [[TSK-1038]]\n", encoding="utf-8"
    )
    (tmp_path / "TSK-1038.md").write_text(
        "## TSK-1038 인터페이스 정의서\n상태: #미확정\n", encoding="utf-8"
    )
    (tmp_path / "meetings" / "kickoff.md").write_text(
        "킥오프. [[TSK-1038]] 논의.\n", encoding="utf-8"
    )
    return ObsidianVault(root=tmp_path, scopes={})


def test_vault_reads_markdown_files_and_skips_obsidian_internals(tmp_path: Path) -> None:
    notes = _vault(tmp_path).list_notes("prj-daon")

    titles = {note.title for note in notes}
    assert titles == {"MTG-088", "TSK-1038", "kickoff"}


def test_wikilinks_become_backlinks_on_the_target_note(tmp_path: Path) -> None:
    notes = {note.title: note for note in _vault(tmp_path).list_notes("prj-daon")}

    backlinks = {link.label for link in notes["TSK-1038"].backlinks}
    assert backlinks == {"MTG-088", "kickoff"}


def test_folder_name_decides_the_note_source(tmp_path: Path) -> None:
    notes = {note.title: note for note in _vault(tmp_path).list_notes("prj-daon")}

    assert notes["kickoff"].source is NoteSource.MEETING
    assert notes["MTG-088"].source is NoteSource.MANUAL


def test_unresolved_tag_surfaces_as_a_warning(tmp_path: Path) -> None:
    notes = {note.title: note for note in _vault(tmp_path).list_notes("prj-daon")}

    assert notes["TSK-1038"].warning == "미확정 태그"


def test_task_code_is_extracted_from_note_content(tmp_path: Path) -> None:
    notes = {note.title: note for note in _vault(tmp_path).list_notes("prj-daon")}

    assert notes["TSK-1038"].task_code == "TSK-1038"


def test_status_reports_the_real_path_and_count(tmp_path: Path) -> None:
    status = _vault(tmp_path).status("prj-daon")

    assert status is not None
    assert status.note_count == 3
    assert status.vault_path == str(tmp_path)


def test_missing_vault_directory_is_reported_as_failed(tmp_path: Path) -> None:
    status = ObsidianVault(root=tmp_path / "absent", scopes={}).status("prj-daon")

    assert status is not None
    assert status.health.value == "failed"
    assert status.note_count == 0


def test_creating_a_note_writes_a_file_obsidian_can_open(tmp_path: Path) -> None:
    vault = _vault(tmp_path)

    vault.create_note(
        Note(
            id="note-mail-002",
            project_id="prj-daon",
            title="필드 매핑 표 회신",
            source=NoteSource.MAIL,
            note_count=1,
            updated_at=None,
            body="## 필드 매핑 표 회신\n출처: 메일 mail-002\n",
        )
    )

    written = tmp_path / "필드 매핑 표 회신.md"
    assert written.is_file()
    assert "mail-002" in written.read_text(encoding="utf-8")


def test_creating_a_note_never_overwrites_existing_text(tmp_path: Path) -> None:
    """볼트는 사용자의 것이다. 같은 이름이 있으면 덮지 않고 옆에 쓴다."""

    vault = _vault(tmp_path)
    original = (tmp_path / "TSK-1038.md").read_text(encoding="utf-8")

    vault.create_note(
        Note(
            id="dup",
            project_id="prj-daon",
            title="TSK-1038",
            source=NoteSource.MAIL,
            note_count=1,
            updated_at=None,
            body="새 내용\n",
        )
    )

    assert (tmp_path / "TSK-1038.md").read_text(encoding="utf-8") == original
    assert (tmp_path / "TSK-1038-dup.md").is_file()
