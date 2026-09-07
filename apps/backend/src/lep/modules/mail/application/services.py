"""Mail use cases: classification review, knowledge promotion, schedule application."""

from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta
from typing import Protocol

from ....common.problems import not_found, state_conflict
from ...delivery.public import (
    ScheduleShift,
    find_milestone_id_by_code,
    get_delivery_service,
    preview_milestone_shift,
    shift_milestone,
)
from ...knowledge.public import create_note_from
from ...projects.public import require_project
from ..domain.entities import Classification, MailMessage

#: How far a "1주 연기" request moves a milestone. The mail body says a week.
_DEFAULT_DEFERRAL = timedelta(days=7)


class MailPort(Protocol):
    def list_messages(self, project_id: str) -> list[MailMessage]: ...

    def get_message(self, message_id: str) -> MailMessage | None: ...

    def replace_message(self, message: MailMessage) -> MailMessage: ...

    def unclassified_count(self, project_id: str) -> int: ...


class MailService:
    def __init__(self, adapter: MailPort) -> None:
        self._adapter = adapter

    def list_messages(self, project_id: str) -> list[MailMessage]:
        require_project(project_id)
        return self._adapter.list_messages(project_id)

    def get_message(self, message_id: str) -> MailMessage:
        message = self._adapter.get_message(message_id)
        if message is None:
            raise not_found(f"메일을 찾을 수 없습니다: {message_id}")
        return message

    def unclassified_count(self, project_id: str) -> int:
        return self._adapter.unclassified_count(project_id)

    def promote_to_note(self, message_id: str) -> str:
        """Turn a message into a vault note through the knowledge module's
        public interface. Mail never writes knowledge's storage itself."""

        message = self.get_message(message_id)
        if message.project_id is None:
            raise state_conflict("프로젝트가 정해지지 않은 메일은 지식화할 수 없습니다.")
        if message.note_id is not None:
            raise state_conflict("이미 지식화된 메일입니다.")

        note_id = f"note-{message.id}"
        create_note_from(
            message.project_id,
            note_id=note_id,
            title=message.subject,
            body=f"## {message.subject}\n출처: 메일 {message.id}\n\n{message.body}\n",
            source="mail",
        )
        self._adapter.replace_message(
            replace(message, note_id=note_id, classification=Classification.PROJECT)
        )
        return note_id

    def preview_schedule_impact(self, message_id: str) -> list[ScheduleShift]:
        """What the mail's implied date change would do. Shown before applying."""

        message = self.get_message(message_id)
        milestone_id, new_end = self._resolve_shift(message)
        return preview_milestone_shift(milestone_id, new_end)

    def apply_to_wbs(self, message_id: str) -> list[ScheduleShift]:
        message = self.get_message(message_id)
        if message.handled:
            raise state_conflict("이미 처리된 메일입니다.")
        milestone_id, new_end = self._resolve_shift(message)
        shifts = shift_milestone(milestone_id, new_end)
        self._adapter.replace_message(
            replace(message, handled=True, classification=Classification.PROJECT)
        )
        return shifts

    def dismiss(self, message_id: str) -> MailMessage:
        """Record that this message is not about the project after all."""

        message = self.get_message(message_id)
        return self._adapter.replace_message(
            replace(message, classification=Classification.UNRELATED, handled=True)
        )

    def _resolve_shift(self, message: MailMessage) -> tuple[str, date]:
        if message.project_id is None or message.milestone_code is None:
            raise state_conflict("이 메일에는 연결된 마일스톤이 없습니다.")
        milestone_id = find_milestone_id_by_code(message.project_id, message.milestone_code)
        if milestone_id is None:
            raise not_found(f"마일스톤을 찾을 수 없습니다: {message.milestone_code}")

        milestone = get_delivery_service().get_milestone(milestone_id)
        return milestone_id, milestone.end + _DEFAULT_DEFERRAL
