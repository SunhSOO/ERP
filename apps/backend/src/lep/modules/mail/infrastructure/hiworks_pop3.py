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

Sender domain match is a *recommendation* only (``suggested_project_id``), not a
classification (ADR-021). The mailbox itself never decides project/unrelated —
``mail_reviews`` in the database is the sole authority on that, and only a human
approval through :class:`~lep.modules.mail.application.services.MailReviewService`
writes it. Intent detection is a small keyword rule, not a model: the mockup's
"일정 변경 추정 (신뢰도 중)" comes from the local LLM, which arrives in
WP-PKD-033. Until then intent is reported at low confidence so nobody mistakes a
keyword match for an inference.
"""

from __future__ import annotations

import email
import hashlib
import json
import os
import poplib
import re
import ssl
from collections.abc import Iterator
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from email.header import decode_header, make_header
from email.message import Message
from email.utils import parseaddr, parsedate_to_datetime
from html.parser import HTMLParser
from threading import Lock
from time import monotonic

from ..domain.entities import (
    Classification,
    Confidence,
    MailAttachment,
    MailMessage,
)

#: Defaults for Hiworks. Both are overridable; other groupware works by pointing
#: these elsewhere.
DEFAULT_HOST = "pop3s.hiworks.com"
DEFAULT_PORT = 995

#: 목록에 쓸 만큼만 본문을 가져온다. POP3의 TOP은 헤더와 본문 앞부분만 준다.
#: 상세 화면은 그때 전체를 다시 읽는다.
PREVIEW_BODY_LINES = 200
PREVIEW_CACHE_TTL_SECONDS = 30

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


class _TextFromHtml(HTMLParser):
    """HTML 본문에서 읽을 수 있는 글자만 꺼낸다.

    하이웍스에서 오는 메일은 본문이 text/html이고 text/plain이 아예 없다.
    text/plain만 찾으면 본문이 통째로 빈 문자열이 되고, 화면은 내용 없는
    메일처럼 보인다. 의존성을 늘리지 않으려고 표준 라이브러리로 훑는다.
    """

    SKIP = {"script", "style", "head"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._chunks: list[str] = []
        self._depth = 0

    def handle_starttag(self, tag: str, attrs: object) -> None:
        if tag in self.SKIP:
            self._depth += 1
        elif tag in {"br", "p", "div", "tr", "li"}:
            self._chunks.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self.SKIP and self._depth:
            self._depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._depth and data.strip():
            self._chunks.append(data)

    def text(self) -> str:
        joined = "".join(self._chunks)
        # 빈 줄이 줄줄이 남으면 화면에서 본문이 아래로 길게 밀린다.
        return re.sub(r"\n{3,}", "\n\n", re.sub(r"[ \t]+", " ", joined)).strip()


def html_to_text(html: str) -> str:
    parser = _TextFromHtml()
    try:
        parser.feed(html)
    except Exception:  # noqa: BLE001 - 깨진 HTML로 메일 하나를 잃지 않는다
        return re.sub(r"<[^>]+>", " ", html).strip()
    return parser.text()


def _decode_payload(part: Message) -> str:
    payload = part.get_payload(decode=True)
    if isinstance(payload, bytes):
        charset = part.get_content_charset() or "utf-8"
        return payload.decode(charset, errors="replace").strip()
    return str(part.get_payload()).strip()


def body_text(message: Message) -> str:
    """본문 텍스트. text/plain을 먼저 보고, 없으면 text/html에서 꺼낸다."""

    if not message.is_multipart():
        text = _decode_payload(message)
        if message.get_content_type() == "text/html":
            return html_to_text(text)
        return text

    html_fallback = ""
    for part in message.walk():
        if part.get_content_disposition() == "attachment":
            continue
        ctype = part.get_content_type()
        if ctype == "text/plain":
            return _decode_payload(part)
        if ctype == "text/html" and not html_fallback:
            html_fallback = _decode_payload(part)

    return html_to_text(html_fallback) if html_fallback else ""


def attachments_of(message: Message) -> tuple[MailAttachment, ...]:
    """딸려 온 파일 목록. 내용은 읽지 않고 이름과 크기만 센다."""

    found: list[MailAttachment] = []
    for index, part in enumerate(message.walk()):
        if part.get_content_maintype() == "multipart":
            continue
        filename = part.get_filename()
        is_attachment = part.get_content_disposition() == "attachment" or bool(filename)
        if not is_attachment:
            continue
        payload = part.get_payload(decode=True)
        found.append(
            MailAttachment(
                # 파일명도 RFC 2047로 인코딩돼 온다. 디코딩하지 않으면 화면에
                # `=?utf-8?B?...?=`가 그대로 뜬다.
                filename=decode(filename) or f"첨부-{index}",
                content_type=part.get_content_type(),
                size_bytes=len(payload) if isinstance(payload, bytes) else 0,
                part_index=index,
            )
        )
    return tuple(found)


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

    Real classification/approval state (unclassified/project/unrelated,
    ``project_id``, ``approved_by``) lives only in the ``mail_reviews`` table
    now (ADR-021, WP-PKD-MAIL-APPROVAL-20260909) and is never read from or
    written to this adapter. What remains here is a same-process, per-UIDL
    overlay of legacy display-only flags (지식화됨, 처리됨) kept only for
    backward compatibility with code that still calls
    :meth:`replace_message`; it resets with the process and is never treated
    as an approval record, matching the fixture adapter's contract.
    """

    host: str
    port: int
    user: str
    password: str
    limit: int = DEFAULT_LIMIT
    domains: dict[str, str] | None = None
    _overlay: dict[str, MailMessage] = field(
        init=False, repr=False, default_factory=dict
    )
    _cache_messages: list[MailMessage] | None = field(
        init=False, repr=False, default=None
    )
    _cache_fetched_at: float | None = field(init=False, repr=False, default=None)
    _cache_signature: tuple[
        str, int, str, str, int, tuple[tuple[str, str], ...]
    ] | None = field(init=False, repr=False, default=None)
    _cache_lock: Lock = field(init=False, repr=False, default_factory=Lock)

    def __post_init__(self) -> None:
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

    def _cache_identity(self) -> tuple[str, int, str, str, int, tuple[tuple[str, str], ...]]:
        domain_items = tuple(sorted((self.domains or {}).items()))
        password_fingerprint = hashlib.sha256(self.password.encode("utf-8")).hexdigest()
        return (
            self.host,
            self.port,
            self.user,
            password_fingerprint,
            self.limit,
            domain_items,
        )

    def _clear_cache(self) -> None:
        self._cache_messages = None
        self._cache_fetched_at = None

    def _snapshot(self) -> list[MailMessage]:
        """Return cached raw preview messages (deep copy) for this cache identity."""
        while True:
            with self._cache_lock:
                identity = self._cache_identity()

                if self._cache_signature != identity:
                    self._cache_signature = identity
                    self._clear_cache()

                now = monotonic()
                if (
                    self._cache_messages is not None
                    and self._cache_fetched_at is not None
                    and now - self._cache_fetched_at < PREVIEW_CACHE_TTL_SECONDS
                ):
                    return deepcopy(self._cache_messages)

                fresh = self._fetch()
                current_identity = self._cache_identity()
                if current_identity != identity:
                    self._cache_signature = current_identity
                    self._clear_cache()
                    continue

                self._cache_messages = deepcopy(fresh)
                self._cache_fetched_at = monotonic()
                self._cache_signature = identity
                return deepcopy(self._cache_messages)

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

        # ADR-021: 발신 도메인 일치는 추천일 뿐이다. project_id는 사람이 승인해야만
        # 채워진다(mail application의 DB). 여기서는 항상 None이고, 분류는 항상
        # unclassified다 — 실제 상태는 리뷰 테이블에만 있다.
        suggested_project_id = (self.domains or {}).get(domain)
        intent = detect_intent(subject, body) if suggested_project_id else None

        return MailMessage(
            id=uid,
            sender_name=display_name or address or "알 수 없음",
            sender_org=domain or "알 수 없음",
            received_at=received,
            subject=subject or "(제목 없음)",
            body=body,
            classification=Classification.UNCLASSIFIED,
            project_id=None,
            intent=intent,
            # A keyword match is not a model inference. Reporting it as anything
            # above LOW would put a confidence on screen that nothing earned.
            confidence=Confidence.LOW if intent else None,
            milestone_code=detect_milestone(subject, body) if suggested_project_id else None,
            attachments=attachments_of(message),
            suggested_project_id=suggested_project_id,
        )

    def fetch_attachment(self, uid: str, part_index: int) -> tuple[str, str, bytes] | None:
        """첨부 하나를 실제로 읽는다. ``(파일명, 콘텐츠 타입, 내용)``.

        목록에는 이름과 크기만 있다. 3.6MB짜리 zip이 오가는 메일함이라
        목록을 만들 때마다 전부 실어 나르면 화면이 그 무게를 그대로 진다.

        본문 MIME part(예: text/html)는 첨부가 아니다. 실제 첨부 판정
        (파일명 또는 attachment disposition)을 통과하지 못하면 내주지 않는다.
        """

        with self._connection() as client:
            count, _ = client.stat()
            if not count:
                return None
            _, uid_lines, _ = client.uidl()
            for raw in uid_lines:
                parts = raw.decode("ascii", errors="replace").split()
                if len(parts) < 2 or parts[1] != uid or not parts[0].isdigit():
                    continue
                _, lines, _ = client.retr(int(parts[0]))
                message = email.message_from_bytes(b"\n".join(lines))
                for index, part in enumerate(message.walk()):
                    if index != part_index:
                        continue
                    if part.get_content_maintype() == "multipart":
                        return None
                    filename = part.get_filename()
                    is_attachment = (
                        part.get_content_disposition() == "attachment" or bool(filename)
                    )
                    if not is_attachment:
                        return None
                    payload = part.get_payload(decode=True)
                    if not isinstance(payload, bytes):
                        return None
                    return (decode(filename) or f"첨부-{index}", part.get_content_type(), payload)
        return None

    def _with_overlay(self, message: MailMessage) -> MailMessage:
        """레거시 처리 표시(지식화됨 등)만 덧입힌다.

        ``classification``/``project_id``/``approved_by``는 절대 덧입히지
        않는다 — 이 overlay는 프로세스 메모리일 뿐이고, 사람 승인의 대체물이
        아니다(ADR-021).
        """

        assert self._overlay is not None
        stored = self._overlay.get(message.id)
        if stored is None:
            return message
        return replace(message, note_id=stored.note_id, handled=stored.handled)

    # ── MailPort ───────────────────────────────────────────────────────────
    @property
    def mailbox_key(self) -> str:
        """ADR-021: host/port/user의 비가역 해시. 비밀번호는 넣지 않는다."""

        canonical = f"hiworks:{self.host}:{self.port}:{self.user}"
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def list_recent(self) -> list[MailMessage]:
        raw_messages = self._snapshot()
        return [self._with_overlay(message) for message in raw_messages]

    def get_message(self, message_id: str) -> MailMessage | None:
        # 목록은 본문 앞부분만 갖고 있다. 상세는 전체를 다시 읽는다.
        message = self._fetch_full(message_id)
        return self._with_overlay(message) if message is not None else None

    def replace_message(self, message: MailMessage) -> MailMessage:
        """레거시 overlay 기록. handled/note_id만 보관한다 (ADR-021)."""

        assert self._overlay is not None
        self._overlay[message.id] = message
        return message
