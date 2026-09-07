"""Hiworks mail adapter over IMAP (WP-PKD-034, ADR-018).

Hiworks is Gabia's groupware. Its mail can be reached with the standard IMAP and
SMTP endpoints once POP3/IMAP is enabled in 메일 > 환경설정 > 기본 설정. Reading
over IMAP avoids the groupware API application process entirely and is
non-destructive: this adapter never deletes, moves or marks a message.

Everything is stdlib. ``imaplib`` and ``email`` are enough, so deploying to the
company server adds no dependency.

Classification is by sender domain, configured per project. Intent detection is a
small keyword rule, not a model: the mockup's "일정 변경 추정 (신뢰도 중)" comes
from the local LLM, which arrives in WP-PKD-033. Until then intent is reported at
low confidence so nobody mistakes a keyword match for an inference.
"""

from __future__ import annotations

import email
import imaplib
import json
import os
import re
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from email.header import decode_header, make_header
from email.message import Message
from email.utils import parseaddr, parsedate_to_datetime

from ..domain.entities import Classification, Confidence, MailMessage

#: Defaults for Hiworks. Both are overridable; other groupware works by pointing
#: these elsewhere.
DEFAULT_HOST = "imaps.hiworks.com"
DEFAULT_PORT = 993
DEFAULT_FOLDER = "INBOX"

#: How many recent messages to read. The mailbox screen shows a working set, not
#: an archive.
DEFAULT_LIMIT = 50

TIMEOUT_SECONDS = 20

#: Keyword rules. Deliberately small and readable — this is a placeholder for the
#: model, and pretending otherwise would put a false confidence on screen.
INTENT_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("일정 변경", ("연기", "일정 변경", "기한 변경", "미뤄", "늦어")),
    ("범위 문의", ("범위", "포함되는지", "해석")),
    ("정산 문의", ("정산", "청구", "대금", "지급")),
    ("자료 회신", ("회신", "첨부", "송부", "전달드립니다")),
]

MILESTONE_CODE = re.compile(r"\bM\d+\b")


def imap_host() -> str:
    return os.getenv("LEP_HIWORKS_HOST", DEFAULT_HOST)


def imap_port() -> int:
    raw = os.getenv("LEP_HIWORKS_PORT", str(DEFAULT_PORT))
    try:
        return int(raw)
    except ValueError:
        return DEFAULT_PORT


def imap_user() -> str | None:
    return os.getenv("LEP_HIWORKS_USER") or None


def imap_password() -> str | None:
    return os.getenv("LEP_HIWORKS_PASSWORD") or None


def project_domains() -> dict[str, str]:
    """Sender domain to project ID. ``{"daon-corp.example": "prj-daon"}``."""

    raw = os.getenv("LEP_HIWORKS_PROJECT_DOMAINS")
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return {str(k).lower(): str(v) for k, v in parsed.items()} if isinstance(parsed, dict) else {}


def decode(value: str | None) -> str:
    """Decode an RFC 2047 header. Korean subjects arrive base64-encoded."""

    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except (UnicodeDecodeError, LookupError, ValueError):
        return value


def body_text(message: Message) -> str:
    """The plain-text body, falling back to whatever the message offers."""

    if message.is_multipart():
        for part in message.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                if isinstance(payload, bytes):
                    charset = part.get_content_charset() or "utf-8"
                    return payload.decode(charset, errors="replace").strip()
        return ""

    payload = message.get_payload(decode=True)
    if isinstance(payload, bytes):
        charset = message.get_content_charset() or "utf-8"
        return payload.decode(charset, errors="replace").strip()
    return str(message.get_payload()).strip()


def detect_intent(subject: str, body: str) -> str | None:
    haystack = f"{subject}\n{body}"
    for intent, keywords in INTENT_KEYWORDS:
        if any(keyword in haystack for keyword in keywords):
            return intent
    return None


def detect_milestone(subject: str, body: str) -> str | None:
    match = MILESTONE_CODE.search(f"{subject}\n{body}")
    return match.group(0) if match else None


@dataclass
class HiworksMailAdapter:
    """Reads a Hiworks mailbox over IMAP.

    Per-message workflow state (지식화됨, 처리됨) does not belong on the mail
    server, so it is held here as an overlay keyed by message ID. WP-PKD-020
    moves the overlay into PostgreSQL; until then it resets with the process,
    which is the same contract the fixture adapter has.
    """

    host: str
    port: int
    user: str
    password: str
    folder: str = DEFAULT_FOLDER
    limit: int = DEFAULT_LIMIT
    domains: dict[str, str] | None = None
    _overlay: dict[str, MailMessage] | None = None

    def __post_init__(self) -> None:
        self._overlay = {}
        if self.domains is None:
            self.domains = project_domains()

    @classmethod
    def from_env(cls) -> HiworksMailAdapter:
        user = imap_user()
        password = imap_password()
        if not user or not password:
            raise ValueError("LEP_HIWORKS_USER와 LEP_HIWORKS_PASSWORD가 필요합니다.")
        return cls(
            host=imap_host(),
            port=imap_port(),
            user=user,
            password=password,
            folder=os.getenv("LEP_HIWORKS_FOLDER", DEFAULT_FOLDER),
        )

    @contextmanager
    def _connection(self) -> Iterator[imaplib.IMAP4_SSL]:
        client = imaplib.IMAP4_SSL(self.host, self.port, timeout=TIMEOUT_SECONDS)
        try:
            client.login(self.user, self.password)
            # Read-only. The mailbox belongs to the person, not to this tool.
            client.select(self.folder, readonly=True)
            yield client
        finally:
            try:
                client.logout()
            except (imaplib.IMAP4.error, OSError):
                pass

    def _fetch(self) -> list[MailMessage]:
        with self._connection() as client:
            status, data = client.search(None, "ALL")
            if status != "OK" or not data or not data[0]:
                return []

            ids = data[0].split()[-self.limit :]
            messages: list[MailMessage] = []
            for raw_id in reversed(ids):
                status, payload = client.fetch(raw_id, "(RFC822)")
                if status != "OK" or not payload:
                    continue
                first = payload[0]
                if not isinstance(first, tuple) or not isinstance(first[1], bytes):
                    continue
                parsed = self._to_message(email.message_from_bytes(first[1]))
                if parsed is not None:
                    messages.append(parsed)
            return messages

    def _to_message(self, message: Message) -> MailMessage | None:
        message_id = decode(message.get("Message-ID")).strip("<>")
        if not message_id:
            return None

        display_name, address = parseaddr(decode(message.get("From")))
        domain = address.split("@")[-1].lower() if "@" in address else ""
        subject = decode(message.get("Subject"))
        body = body_text(message)

        try:
            received = parsedate_to_datetime(message.get("Date", ""))
        except (TypeError, ValueError):
            received = datetime.now(tz=UTC)
        if received.tzinfo is None:
            received = received.replace(tzinfo=UTC)

        project_id = (self.domains or {}).get(domain)
        intent = detect_intent(subject, body) if project_id else None

        return MailMessage(
            id=message_id,
            sender_name=display_name or address or "알 수 없음",
            sender_org=domain or "알 수 없음",
            received_at=received,
            subject=subject or "(제목 없음)",
            body=body,
            classification=(
                Classification.UNCLASSIFIED if project_id and intent else
                Classification.PROJECT if project_id else
                Classification.UNRELATED
            ),
            project_id=project_id,
            intent=intent,
            # A keyword match is not a model inference. Reporting it as anything
            # above LOW would put a confidence on screen that nothing earned.
            confidence=Confidence.LOW if intent else None,
            milestone_code=detect_milestone(subject, body) if project_id else None,
        )

    def _with_overlay(self, message: MailMessage) -> MailMessage:
        assert self._overlay is not None
        stored = self._overlay.get(message.id)
        if stored is None:
            return message
        return replace(
            message,
            classification=stored.classification,
            note_id=stored.note_id,
            handled=stored.handled,
        )

    # ── MailPort ───────────────────────────────────────────────────────────
    def list_messages(self, project_id: str) -> list[MailMessage]:
        return [
            self._with_overlay(message)
            for message in self._fetch()
            if message.project_id == project_id
            or message.classification is Classification.UNRELATED
        ]

    def get_message(self, message_id: str) -> MailMessage | None:
        for message in self._fetch():
            if message.id == message_id:
                return self._with_overlay(message)
        return None

    def replace_message(self, message: MailMessage) -> MailMessage:
        assert self._overlay is not None
        self._overlay[message.id] = message
        return message

    def unclassified_count(self, project_id: str) -> int:
        return len(
            [
                message
                for message in self.list_messages(project_id)
                if message.project_id == project_id
                and message.classification is Classification.UNCLASSIFIED
                and not message.handled
            ]
        )
