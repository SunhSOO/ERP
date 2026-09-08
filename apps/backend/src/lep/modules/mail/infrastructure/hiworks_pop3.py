"""Hiworks mail adapter over POP3 (WP-PKD-034, ADR-018).

Hiworks is Gabia's groupware. **It does not offer IMAP.** ``imaps.hiworks.com``
does not resolve, and port 993 answers on none of its hosts. Only POP3S on
``pop3s.hiworks.com:995`` is reachable, which the server confirms with an
``+OK Hiworks-POP3S`` banner. An earlier version of this adapter assumed IMAP
and could never have worked.

Two consequences follow from POP3 being all there is.

**Never send DELE.** In IMAP a careless client marks a flag; in POP3 it destroys
mail, and this is somebody's real work mailbox. This adapter issues USER, PASS,
STAT, UIDL, TOP, RETR and QUIT — nothing else — and sends RSET before quitting so
that even a bug upstream cannot commit a deletion.

**Messages are identified by UIDL**, the server's own per-mailbox unique id,
rather than the ``Message-ID`` header, which is optional and occasionally absent.

Reading over POP3 also avoids the groupware API application process entirely.

Everything is stdlib. ``poplib`` and ``email`` are enough, so deploying to the
company server adds no dependency.

Classification is by sender domain, configured per project. Intent detection is a
small keyword rule, not a model: the mockup's "일정 변경 추정 (신뢰도 중)" comes
from the local LLM, which arrives in WP-PKD-033. Until then intent is reported at
low confidence so nobody mistakes a keyword match for an inference.
"""

from __future__ import annotations

import email
import json
import os
import poplib
import re
import ssl
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
DEFAULT_HOST = "pop3s.hiworks.com"
DEFAULT_PORT = 995

#: 목록에 쓸 만큼만 본문을 가져온다. POP3의 TOP은 헤더와 본문 앞부분만 준다.
#: 상세 화면은 그때 전체를 다시 읽는다.
PREVIEW_BODY_LINES = 200

#: How many recent messages to read.
#:
#: POP3 has no server-side search, so finding a project's mail means pulling
#: headers for the newest N and filtering here. 50 was too few on a real
#: mailbox: 721 messages, of which the client's five sat well outside the most
#: recent fifty because internal mail dominates the traffic. Reading is roughly
#: 12 messages a second, so this trades page latency for reach.
DEFAULT_LIMIT = 300

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


def mail_host() -> str:
    return os.getenv("LEP_HIWORKS_HOST", DEFAULT_HOST)


def mail_port() -> int:
    raw = os.getenv("LEP_HIWORKS_PORT", str(DEFAULT_PORT))
    try:
        return int(raw)
    except ValueError:
        return DEFAULT_PORT


def mail_user() -> str | None:
    return os.getenv("LEP_HIWORKS_USER") or None


def mail_password() -> str | None:
    """하이웍스의 **메일 전용 비밀번호**.

    계정 로그인 비밀번호가 아니다. 하이웍스는 [내 정보 > 설정 > 보안 설정 >
    메일 전용 비밀번호]에서 무작위 비밀번호를 따로 만들게 하고, 그것을 만들면
    로그인 비밀번호로는 외부 접속이 막힌다. 2단계 인증을 쓰면 필수다.
    """

    return os.getenv("LEP_HIWORKS_PASSWORD") or None


def mail_limit() -> int:
    raw = os.getenv("LEP_HIWORKS_LIMIT", str(DEFAULT_LIMIT))
    try:
        return max(1, int(raw))
    except ValueError:
        return DEFAULT_LIMIT


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
    """Reads a Hiworks mailbox over POP3, without ever changing it.

    Per-message workflow state (지식화됨, 처리됨) does not belong on the mail
    server, so it is held here as an overlay keyed by UIDL. WP-PKD-020 moves the
    overlay into PostgreSQL; until then it resets with the process, which is the
    same contract the fixture adapter has.
    """

    host: str
    port: int
    user: str
    password: str
    limit: int = DEFAULT_LIMIT
    domains: dict[str, str] | None = None
    _overlay: dict[str, MailMessage] | None = None

    def __post_init__(self) -> None:
        self._overlay = {}
        if self.domains is None:
            self.domains = project_domains()

    @classmethod
    def from_env(cls) -> HiworksMailAdapter:
        user = mail_user()
        password = mail_password()
        if not user or not password:
            raise ValueError("LEP_HIWORKS_USER와 LEP_HIWORKS_PASSWORD가 필요합니다.")
        return cls(
            host=mail_host(),
            port=mail_port(),
            user=user,
            password=password,
            limit=mail_limit(),
        )

    @contextmanager
    def _connection(self) -> Iterator[poplib.POP3_SSL]:
        """POP3 세션 하나. 메일함을 잠그므로 짧게 쓰고 바로 닫는다."""

        client = poplib.POP3_SSL(
            self.host, self.port, timeout=TIMEOUT_SECONDS,
            context=ssl.create_default_context(),
        )
        try:
            client.user(self.user)
            client.pass_(self.password)
            yield client
        finally:
            try:
                # RSET은 삭제 표시를 되돌린다. 우리는 DELE을 보내지 않지만,
                # QUIT이 삭제를 확정하는 프로토콜에서 이 한 줄은 값싼 보험이다.
                client.rset()
            except (poplib.error_proto, OSError):
                pass
            try:
                client.quit()
            except (poplib.error_proto, OSError):
                pass

    def _fetch(self) -> list[MailMessage]:
        """최근 메일의 헤더와 본문 앞부분을 읽는다.

        전체를 받지 않는다. 목록 화면에 필요한 것은 보낸 사람, 제목, 분류에
        쓸 본문 앞부분뿐이고, 50통을 통째로 받으면 첨부까지 딸려 온다.
        """

        with self._connection() as client:
            count, _ = client.stat()
            if not count:
                return []

            _, uid_lines, _ = client.uidl()
            uids: dict[int, str] = {}
            for raw in uid_lines:
                parts = raw.decode("ascii", errors="replace").split()
                if len(parts) >= 2 and parts[0].isdigit():
                    uids[int(parts[0])] = parts[1]

            newest = range(count, max(count - self.limit, 0), -1)
            messages: list[MailMessage] = []
            for number in newest:
                uid = uids.get(number)
                if uid is None:
                    continue
                try:
                    _, lines, _ = client.top(number, PREVIEW_BODY_LINES)
                except poplib.error_proto:
                    continue
                parsed = self._to_message(
                    email.message_from_bytes(b"\n".join(lines)), uid
                )
                if parsed is not None:
                    messages.append(parsed)
            return messages

    def _fetch_full(self, uid: str) -> MailMessage | None:
        """한 통을 전체로 읽는다. 상세 화면에서만 쓴다."""

        with self._connection() as client:
            count, _ = client.stat()
            if not count:
                return None
            _, uid_lines, _ = client.uidl()
            for raw in uid_lines:
                parts = raw.decode("ascii", errors="replace").split()
                if len(parts) >= 2 and parts[1] == uid and parts[0].isdigit():
                    _, lines, _ = client.retr(int(parts[0]))
                    return self._to_message(
                        email.message_from_bytes(b"\n".join(lines)), uid
                    )
        return None

    def _to_message(self, message: Message, uid: str) -> MailMessage | None:
        # 식별자는 서버가 준 UIDL이다. Message-ID 헤더는 선택 사항이라
        # 없는 메일이 있고, 없으면 그 메일만 조용히 목록에서 사라진다.
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
            id=uid,
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
        # 목록은 본문 앞부분만 갖고 있다. 상세는 전체를 다시 읽는다.
        message = self._fetch_full(message_id)
        return self._with_overlay(message) if message is not None else None

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
