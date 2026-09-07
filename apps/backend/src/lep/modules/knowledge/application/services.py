"""Knowledge use cases: vault reads, meeting application, change preview."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from enum import StrEnum

from ....common.problems import ProblemError, not_found, state_conflict
from ...delivery.public import (
    ScheduleShift,
    find_milestone_id_by_code,
    preview_milestone_shift,
    shift_milestone,
)
from ...projects.public import require_project
from ..domain.entities import (
    ActionItem,
    ApplyStatus,
    Decision,
    Meeting,
    Note,
    NoteSource,
    VaultStatus,
)
from ..domain.ports import MeetingRepository, VaultPort


class ApplyMode(StrEnum):
    """What to do with a meeting's pending outcomes. Mirrors the three buttons on
    screen 08: WBS에 반영 / 볼트에만 지식화 / 무시."""

    WBS = "wbs"
    VAULT_ONLY = "vault_only"
    DISMISS = "dismiss"


@dataclass(frozen=True, slots=True)
class ApplyPreview:
    """What applying a meeting would change. Shown before the user confirms."""

    milestone_code: str | None
    old_end: date | None
    new_end: date | None
    shifts: list[ScheduleShift]


class KnowledgeService:
    def __init__(self, vault: VaultPort, meetings: MeetingRepository) -> None:
        self._vault = vault
        self._meetings = meetings

    # ── vault ──────────────────────────────────────────────────────────────
    def get_vault_status(self, project_id: str) -> VaultStatus:
        require_project(project_id)
        status = self._vault.status(project_id)
        if status is None:
            raise not_found(f"볼트 상태를 찾을 수 없습니다: {project_id}")
        return status

    def list_notes(self, project_id: str) -> list[Note]:
        require_project(project_id)
        return self._vault.list_notes(project_id)

    def get_note(self, note_id: str) -> Note:
        note = self._vault.get_note(note_id)
        if note is None:
            raise not_found(f"노트를 찾을 수 없습니다: {note_id}")
        return note

    def resync(self, project_id: str) -> VaultStatus:
        require_project(project_id)
        return self._vault.resync(project_id)

    def create_note(
        self,
        project_id: str,
        *,
        note_id: str,
        title: str,
        body: str,
        source: NoteSource,
    ) -> Note:
        require_project(project_id)
        if self._vault.get_note(note_id) is not None:
            raise state_conflict(f"이미 존재하는 노트입니다: {note_id}")
        return self._vault.create_note(
            Note(
                id=note_id,
                project_id=project_id,
                title=title,
                source=source,
                note_count=1,
                updated_at=date.today(),
                body=body,
            )
        )

    # ── meetings ───────────────────────────────────────────────────────────
    def list_meetings(self, project_id: str) -> list[Meeting]:
        require_project(project_id)
        return self._meetings.list_meetings(project_id)

    def get_meeting(self, meeting_id: str) -> Meeting:
        meeting = self._meetings.get_meeting(meeting_id)
        if meeting is None:
            raise not_found(f"회의록을 찾을 수 없습니다: {meeting_id}")
        return meeting

    def list_decisions(self, meeting_id: str) -> list[Decision]:
        self.get_meeting(meeting_id)
        return self._meetings.list_decisions(meeting_id)

    def list_action_items(self, meeting_id: str) -> list[ActionItem]:
        self.get_meeting(meeting_id)
        return self._meetings.list_action_items(meeting_id)

    def preview_apply(self, meeting_id: str) -> ApplyPreview:
        """What would change if this meeting's decisions were applied.

        Read-only, and :meth:`apply` calls it, so what the dialog promises is what
        the apply actually does.
        """

        meeting = self.get_meeting(meeting_id)
        pending = [
            decision
            for decision in self._meetings.list_decisions(meeting_id)
            if not decision.applied and decision.milestone_code and decision.new_end
        ]
        if not pending:
            return ApplyPreview(
                milestone_code=None, old_end=None, new_end=None, shifts=[]
            )

        decision = pending[0]
        assert decision.milestone_code is not None
        assert decision.new_end is not None

        milestone_id = find_milestone_id_by_code(meeting.project_id, decision.milestone_code)
        if milestone_id is None:
            raise not_found(f"마일스톤을 찾을 수 없습니다: {decision.milestone_code}")

        return ApplyPreview(
            milestone_code=decision.milestone_code,
            old_end=None,
            new_end=decision.new_end,
            shifts=preview_milestone_shift(milestone_id, decision.new_end),
        )

    def apply(self, meeting_id: str, mode: ApplyMode) -> ApplyPreview:
        """Apply a meeting's outcomes.

        ``WBS`` moves the schedule and writes the vault note. ``VAULT_ONLY`` writes
        only the note. ``DISMISS`` records the decision to do nothing, which is
        still a decision worth keeping.
        """

        meeting = self.get_meeting(meeting_id)
        if meeting.apply_status is not ApplyStatus.PENDING:
            raise state_conflict("이미 처리된 회의록입니다.")

        preview = self.preview_apply(meeting_id)

        if mode is ApplyMode.WBS:
            if preview.milestone_code is None or preview.new_end is None:
                raise ProblemError("STATE_CONFLICT", "WBS에 반영할 일정 변경이 없습니다.")
            milestone_id = find_milestone_id_by_code(
                meeting.project_id, preview.milestone_code
            )
            if milestone_id is None:
                raise not_found(f"마일스톤을 찾을 수 없습니다: {preview.milestone_code}")
            shift_milestone(milestone_id, preview.new_end)

        if mode in (ApplyMode.WBS, ApplyMode.VAULT_ONLY):
            note_id = f"note-{meeting.code.lower()}"
            if self._vault.get_note(note_id) is None:
                self._vault.create_note(
                    Note(
                        id=note_id,
                        project_id=meeting.project_id,
                        title=f"{meeting.code} {meeting.title}",
                        source=NoteSource.MEETING,
                        note_count=1,
                        updated_at=date.today(),
                        body=(
                            f"## {meeting.code} {meeting.title}\n"
                            "회의록에서 자동 생성되었습니다.\n"
                        ),
                    )
                )
            for decision in self._meetings.list_decisions(meeting_id):
                if not decision.applied:
                    self._meetings.replace_decision(replace(decision, applied=True))

        status = (
            ApplyStatus.DISMISSED if mode is ApplyMode.DISMISS else ApplyStatus.APPLIED
        )
        self._meetings.replace_meeting(
            replace(meeting, apply_status=status, pending_count=0)
        )
        return preview
