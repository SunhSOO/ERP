"""Fixture vault and meeting adapters (ADR-018).

목업 데이터다. 실제 고객·직원 정보가 아니다. AGENTS.md 1절 7항.

WP-PKD-032 adds an Obsidian adapter beside this one. Both satisfy ``VaultPort``,
so no screen or service changes when the switch happens.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime

from ..domain.entities import (
    ActionItem,
    ApplyStatus,
    Backlink,
    Decision,
    Meeting,
    Note,
    NoteSource,
    SyncHealth,
    VaultStatus,
)

PRJ_DAON = "prj-daon"

_STATUS: dict[str, VaultStatus] = {
    PRJ_DAON: VaultStatus(
        project_id=PRJ_DAON,
        health=SyncHealth.OK,
        last_sync_at=datetime(2026, 9, 7, 4, 0, tzinfo=UTC),
        note_count=214,
        vault_path="",
    )
}

_NOTES: list[Note] = [
    Note(
        id="note-tsk-1038",
        project_id=PRJ_DAON,
        title="TSK-1038 인터페이스 정의서 v2",
        source=NoteSource.MEETING,
        note_count=3,
        updated_at=date(2026, 9, 5),
        task_code="TSK-1038",
        body=(
            "## TSK-1038 인터페이스 정의서 v2\n"
            "출처: [[MTG-088]] 결정 #2\n"
            "상태: #차단\n"
            "- 필드 매핑 표 미확정 (WMS팀 회신 대기)\n"
            "- 관련: [[TSK-1030]], [[WMS_스펙]]\n"
            "담당: 박도윤\n"
        ),
        backlinks=[
            Backlink(target="MTG-088", label="MTG-088 회의록"),
            Backlink(target="TSK-1030", label="TSK-1030 WMS API 스펙"),
            Backlink(target="MAIL-002", label="메일: WMS팀 회신 요청"),
        ],
    ),
    Note(
        id="note-tsk-1042",
        project_id=PRJ_DAON,
        title="TSK-1042 검수 시나리오 작성",
        source=NoteSource.STATEMENT,
        note_count=2,
        updated_at=date(2026, 9, 1),
        task_code="TSK-1042",
        body="## TSK-1042 검수 시나리오\n출처: 과업지시서 제4조 1항\n",
        backlinks=[Backlink(target="stm-daon-v1", label="과업지시서 제4조 1항")],
    ),
    Note(
        id="note-contract-support",
        project_id=PRJ_DAON,
        title="계약 조건 — 운영 안정화 지원 범위",
        source=NoteSource.MAIL,
        note_count=1,
        updated_at=None,
        body="## 운영 안정화 지원 범위\n계약 해석이 필요하다. 범위가 확정되지 않았다.\n",
        backlinks=[Backlink(target="cls-5-3", label="과업지시서 제5조 3항")],
        warning="미확정 태그",
    ),
    Note(
        id="note-m2-decisions",
        project_id=PRJ_DAON,
        title="M2 설계 결정 로그",
        source=NoteSource.MEETING,
        note_count=6,
        updated_at=date(2026, 8, 20),
        body="## M2 설계 결정 로그\n",
        backlinks=[Backlink(target="MTG-080", label="MTG-080 킥오프 후속 미팅")],
    ),
]

_MEETINGS: list[Meeting] = [
    Meeting(
        id="mtg-088",
        project_id=PRJ_DAON,
        code="MTG-088",
        title="검수 일정 리뷰",
        held_at=datetime(2026, 9, 6, 6, 30, tzinfo=UTC),
        attendees=["김서준", "박도윤", "이서영(다온물산)"],
        apply_status=ApplyStatus.PENDING,
        pending_count=2,
    ),
    Meeting(
        id="mtg-085",
        project_id=PRJ_DAON,
        code="MTG-085",
        title="요구사항 변경 협의",
        held_at=datetime(2026, 9, 1, 6, 0, tzinfo=UTC),
        attendees=["김서준", "박도윤"],
        apply_status=ApplyStatus.APPLIED,
        pending_count=0,
    ),
    Meeting(
        id="mtg-080",
        project_id=PRJ_DAON,
        code="MTG-080",
        title="킥오프 후속 미팅",
        held_at=datetime(2026, 8, 25, 6, 0, tzinfo=UTC),
        attendees=["김서준", "이서영(다온물산)"],
        apply_status=ApplyStatus.APPLIED,
        pending_count=0,
    ),
]

_DECISIONS: list[Decision] = [
    Decision(
        id="dec-088-1",
        meeting_id="mtg-088",
        ordinal=1,
        text="WMS 필드 매핑 표는 09-10까지 회신받기로 함",
        applied=True,
    ),
    Decision(
        id="dec-088-2",
        meeting_id="mtg-088",
        ordinal=2,
        text="검수 일정을 1주 연기 (09-12 → 09-19)",
        applied=False,
        milestone_code="M3",
        new_end=date(2026, 9, 19),
    ),
]

_ACTION_ITEMS: list[ActionItem] = [
    ActionItem(
        id="act-088-1",
        meeting_id="mtg-088",
        text="WMS팀에 필드 매핑 표 재요청",
        owner="박도윤",
        due=date(2026, 9, 8),
        task_created=True,
        needs_approval=False,
    ),
    ActionItem(
        id="act-088-2",
        meeting_id="mtg-088",
        text="M3 마일스톤 기한 09-19로 변경",
        owner="김서준",
        due=None,
        task_created=False,
        needs_approval=True,
    ),
]


class FixtureVault:
    def status(self, project_id: str) -> VaultStatus | None:
        return _STATUS.get(project_id)

    def list_notes(self, project_id: str) -> list[Note]:
        return [note for note in _NOTES if note.project_id == project_id]

    def get_note(self, note_id: str) -> Note | None:
        return next((note for note in _NOTES if note.id == note_id), None)

    def create_note(self, note: Note) -> Note:
        _NOTES.append(note)
        current = _STATUS.get(note.project_id)
        if current is not None:
            _STATUS[note.project_id] = replace(current, note_count=current.note_count + 1)
        return note

    def resync(self, project_id: str) -> VaultStatus:
        current = _STATUS[project_id]
        refreshed = replace(
            current, health=SyncHealth.OK, last_sync_at=datetime.now(tz=UTC)
        )
        _STATUS[project_id] = refreshed
        return refreshed


class FixtureMeetingRepository:
    def list_meetings(self, project_id: str) -> list[Meeting]:
        return [item for item in _MEETINGS if item.project_id == project_id]

    def get_meeting(self, meeting_id: str) -> Meeting | None:
        return next((item for item in _MEETINGS if item.id == meeting_id), None)

    def replace_meeting(self, meeting: Meeting) -> Meeting:
        for index, existing in enumerate(_MEETINGS):
            if existing.id == meeting.id:
                _MEETINGS[index] = meeting
                return meeting
        _MEETINGS.append(meeting)
        return meeting

    def list_decisions(self, meeting_id: str) -> list[Decision]:
        return [item for item in _DECISIONS if item.meeting_id == meeting_id]

    def replace_decision(self, decision: Decision) -> Decision:
        for index, existing in enumerate(_DECISIONS):
            if existing.id == decision.id:
                _DECISIONS[index] = decision
                return decision
        _DECISIONS.append(decision)
        return decision

    def list_action_items(self, meeting_id: str) -> list[ActionItem]:
        return [item for item in _ACTION_ITEMS if item.meeting_id == meeting_id]
