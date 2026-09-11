"""Ports for the mail module (ADR-018, ADR-021).

Classification state (unclassified/project/unrelated), approval identity, and
attachment links live in the mail module's own database tables, never on the
adapter. The adapter only ever hands back what the mailbox itself contains:
raw content and a same-process overlay of legacy per-message flags kept for
backward compatibility. Nothing here is trusted as an approval record.
"""

from __future__ import annotations

from typing import Protocol

from .entities import MailMessage


class MailPort(Protocol):
    @property
    def mailbox_key(self) -> str:
        """Stable, non-reversible identity of the mailbox (ADR-021).

        Hashes host/port/user, excluding the password. Two adapters pointed
        at different accounts never share a key, so switching accounts cannot
        surface another mailbox's review history.
        """
        ...

    def list_recent(self) -> list[MailMessage]:
        """The newest messages the mailbox holds, always reported unclassified.

        Classification is a database concept now; the adapter never decides
        it. ``suggested_project_id`` may still be set from a domain match.
        """
        ...

    def get_message(self, message_id: str) -> MailMessage | None:
        """The full message (not a preview), used at decision time and for detail."""
        ...

    def fetch_attachment(
        self, message_id: str, part_index: int
    ) -> tuple[str, str, bytes] | None:
        """One attachment's ``(filename, content_type, bytes)``, or ``None``.

        Rejects any part that is not an actual attachment (no filename, no
        attachment disposition) — never exposes a body MIME part this way.
        """
        ...
