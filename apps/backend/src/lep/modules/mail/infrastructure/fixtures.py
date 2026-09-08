"""Empty mail adapter.

There is no seeded mail. Until a Hiworks account is configured the mailbox is
genuinely empty, and the screen says so rather than showing invented messages.

Configuring `LEP_ADAPTER_MAIL=hiworks` swaps this for the IMAP adapter, which
reads the real mailbox. See `hiworks_imap.py`.
"""

from __future__ import annotations

from ..domain.entities import MailMessage


class EmptyMailAdapter:
    """The mail port with nothing behind it."""

    def list_messages(self, project_id: str) -> list[MailMessage]:
        return []

    def get_message(self, message_id: str) -> MailMessage | None:
        return None

    def replace_message(self, message: MailMessage) -> MailMessage:
        return message

    def unclassified_count(self, project_id: str) -> int:
        return 0


#: 이전 이름을 쓰던 곳이 있어 별칭을 남긴다.
FixtureMailAdapter = EmptyMailAdapter
