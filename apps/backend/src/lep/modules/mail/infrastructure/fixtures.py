"""Empty mail adapter.

There is no seeded mail. Until a Hiworks account is configured the mailbox is
genuinely empty, and the screen says so rather than showing invented messages.

Configuring `LEP_ADAPTER_MAIL=hiworks` swaps this for the IMAP adapter, which
reads the real mailbox. See `hiworks_pop3.py`.
"""

from __future__ import annotations

import hashlib

from ..domain.entities import MailMessage

#: ADR-021: 계정마다 갈라야 할 이유가 없는 고정 네임스페이스. 실제 어댑터가
#: 없으므로 언제나 이 값 하나뿐이고, 승인 이력이 뒤섞일 계정이 없다.
#: documents 쪽 계약(mail_backend/mail_links)이 mailbox_key를 SHA-256 64자
#: 16진수로만 받으므로, 고정 문자열이 아니라 그 문자열의 해시를 쓴다.
EMPTY_MAILBOX_KEY = hashlib.sha256(b"fixture-empty-mailbox").hexdigest()


class EmptyMailAdapter:
    """The mail port with nothing behind it."""

    @property
    def mailbox_key(self) -> str:
        return EMPTY_MAILBOX_KEY

    def list_recent(self) -> list[MailMessage]:
        return []

    def get_message(self, message_id: str) -> MailMessage | None:
        return None

    def fetch_attachment(
        self, message_id: str, part_index: int
    ) -> tuple[str, str, bytes] | None:
        """메일이 없으므로 첨부도 없다."""

        return None


#: 이전 이름을 쓰던 곳이 있어 별칭을 남긴다.
FixtureMailAdapter = EmptyMailAdapter
