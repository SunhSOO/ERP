"""Mail use cases: classification review and knowledge promotion.

The mailbox is read-only. Per-message workflow state lives in the adapter's
overlay, not on the mail server.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Protocol

from ....common.problems import not_found, state_conflict
from ...knowledge.public import create_note_from
from ..domain.entities import Classification, MailMessage


class MailPort(Protocol):
    def list_messages(self, project_id: str) -> list[MailMessage]: ...

    def get_message(self, message_id: str) -> MailMessage | None: ...

    def replace_message(self, message: MailMessage) -> MailMessage: ...

    def unclassified_count(self, project_id: str) -> int: ...


class MailService:
    def __init__(self, adapter: MailPort) -> None:
        self._adapter = adapter

    def list_messages(self, project_id: str) -> list[MailMessage]:
        return self._adapter.list_messages(project_id)

    def get_message(self, message_id: str) -> MailMessage:
        message = self._adapter.get_message(message_id)
        if message is None:
            raise not_found(f"메일을 찾을 수 없습니다: {message_id}")
        return message

    def unclassified_count(self, project_id: str) -> int:
        return self._adapter.unclassified_count(project_id)

    def promote_to_note(self, message_id: str, *, project_code: str) -> str:
        """메일을 볼트 노트로 만든다.

        볼트 쓰기는 knowledge 모듈의 public 인터페이스를 지난다. 이 모듈이
        파일을 직접 만들지 않는다.
        """

        message = self.get_message(message_id)
        if message.project_id is None:
            raise state_conflict("프로젝트가 정해지지 않은 메일은 지식화할 수 없습니다.")
        if message.note_id is not None:
            raise state_conflict("이미 지식화된 메일입니다.")

        title = message.subject or "제목 없는 메일"
        stem = create_note_from(
            project_code,
            title=title,
            body=(
                f"# {title}\n\n"
                f"출처: 메일 {message.id}\n"
                f"보낸 사람: {message.sender_name} ({message.sender_org})\n"
                f"받은 시각: {message.received_at.isoformat()}\n\n"
                f"{message.body}\n"
            ),
            folder="inbox",
        )
        self._adapter.replace_message(
            replace(message, note_id=stem, classification=Classification.PROJECT)
        )
        return stem

    def dismiss(self, message_id: str) -> MailMessage:
        """이 메일이 프로젝트와 무관하다고 기록한다."""

        message = self.get_message(message_id)
        return self._adapter.replace_message(
            replace(message, classification=Classification.UNRELATED, handled=True)
        )
