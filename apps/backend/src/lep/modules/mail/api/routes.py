"""Mail HTTP routes (ADR-021).

Every mutating endpoint here is ``sync def`` per WP-PKD-MAIL-APPROVAL-20260909.
Approve/dismiss/attachments-approve each take an ``Idempotency-Key`` header;
``promote-to-note`` does not — it is CAS-guarded on ``note_id`` instead, and
adding a header contract to it now would be a breaking change to whatever
already calls it. Approval/attachment state changes go through
:class:`MailReviewService`, never directly against the adapter.
"""

from __future__ import annotations

import base64
import re
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session as DbSession

from ....common.db import get_session
from ....common.envelope import Envelope, ListEnvelope, collection, single
from ....common.problems import ProblemError
from ...iam.public import CurrentUser, User
from ..application.services import AttachmentSelectionInput, MailReviewService
from ..domain.entities import MailMessage
from ..public import get_mail_service

router = APIRouter(prefix="/api/v1", tags=["mail"])


def _transport_message_id(message_id: str, id_encoding: str | None) -> str:
    """Decode the opt-in URL-safe transport without changing stored UIDLs."""
    if id_encoding is None:
        return message_id
    if id_encoding != "base64url":
        raise ProblemError("VALIDATION_FAILED", "지원하지 않는 id_encoding입니다.")
    if not re.fullmatch(r"[A-Za-z0-9_-]+", message_id) or len(message_id) % 4 == 1:
        raise ProblemError("VALIDATION_FAILED", "잘못된 base64url message_id입니다.")
    padded = message_id + "=" * (-len(message_id) % 4)
    try:
        raw = base64.urlsafe_b64decode(padded).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        raise ProblemError("VALIDATION_FAILED", "잘못된 base64url message_id입니다.") from None
    if (
        not raw
        or len(raw) > 255
        or any(ord(char) < 32 or ord(char) == 127 for char in raw)
        or base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=") != message_id
    ):
        raise ProblemError("VALIDATION_FAILED", "canonical base64url message_id가 아닙니다.")
    return raw

#: text/html 등 브라우저가 실행할 수 있는 타입은 강등한다. nosniff와 함께 쓰는
#: 두 번째 방어선이다. RFC 7230 ``token``으로 ASCII만 받는다 — ``\w``는 유니코드
#: 글자까지 매치해서 비 ASCII MIME 토큰을 통과시키고, Starlette은 응답 헤더를
#: latin-1로 인코딩하다가 그 값에서 인코딩 실패로 500을 낸다.
_MIME_TOKEN = r"[!#$%&'*+\-.^_`|~0-9A-Za-z]+"
_SAFE_CONTENT_TYPE = re.compile(rf"^{_MIME_TOKEN}/{_MIME_TOKEN}$")
_EXECUTABLE_CONTENT_TYPES = frozenset(
    {"text/html", "application/xhtml+xml", "image/svg+xml", "application/javascript"}
)


def _sanitize_content_type(content_type: str) -> str:
    if not content_type or not _SAFE_CONTENT_TYPE.match(content_type):
        return "application/octet-stream"
    if content_type.lower() in _EXECUTABLE_CONTENT_TYPES:
        return "application/octet-stream"
    return content_type


def _sanitize_filename(filename: str) -> str:
    cleaned = (filename or "").replace("/", "_").replace("\\", "_").strip()
    return cleaned or "attachment"


def _filename_fallback(filename: str) -> str:
    """Generate a safe ASCII fallback that preserves the extension."""
    suffix = Path(_sanitize_filename(filename)).suffix
    return f"attachment{suffix[:16]}" if suffix else "attachment"


def _idempotency_key(
    idempotency_key: Annotated[
        str | None,
        Header(
            alias="Idempotency-Key",
            description=(
                "Required on approve/attachments-approve/dismiss. Identical "
                "key + identical request body replays the original result; "
                "the same key with a different body, or reused against an "
                "already-finalized mail, is a 409 conflict. Change the key "
                "whenever the request content changes or after success."
            ),
        ),
    ] = None,
) -> str:
    if idempotency_key is None or not idempotency_key.strip():
        raise ProblemError("VALIDATION_FAILED", "Idempotency-Key 헤더가 필요합니다.")
    return idempotency_key


IdempotencyKey = Annotated[str, Depends(_idempotency_key)]


def _service(db: DbSession, user: User) -> MailReviewService:
    return MailReviewService(db, get_mail_service(), user)


class AttachmentOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    filename: str
    content_type: str
    size_bytes: int
    part_index: int
    linked_file_id: str | None = Field(
        description=(
            "documents drive reference id once this attachment has been "
            "approved and registered; null while pending or unselected. "
            "Pass back as the ?linked_file_id= query on the download "
            "endpoint to guard against a stale link surviving a mailbox "
            "account switch."
        )
    )


class MailProjectSuggestionOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: str
    project_name: str
    confidence: str
    reasons: list[str]


class MailOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    sender_name: str
    sender_org: str
    received_at: datetime
    subject: str
    body: str
    classification: str
    project_id: str | None
    suggested_project_id: str | None = Field(
        description=(
            "Domain-match recommendation only (ADR-021) — never a "
            "classification. Always distinct from project_id, which is set "
            "only by an explicit human approval."
        )
    )
    intent: str | None
    confidence: str | None
    milestone_code: str | None
    note_id: str | None
    handled: bool
    version: int = Field(
        description="Optimistic-concurrency version. Send back as expected_version."
    )
    approved_by: str | None = Field(
        description="Actor id who approved/dismissed this mail; null until a human decides."
    )
    approved_at: datetime | None = Field(
        description="When the mail was approved or dismissed; null until a human decides."
    )
    can_review: bool = Field(
        description="Whether the current actor may approve/dismiss mail (active admin only)."
    )
    attachments: list[AttachmentOut]
    suggestions: list[MailProjectSuggestionOut] = Field(
        default_factory=list,
        description=(
            "Project context recommendations for unclassified mail only (Task 5). "
            "Up to 3 candidates ranked by score. Empty for classified or no-match messages."
        )
    )

    @classmethod
    def of(cls, m: MailMessage, actor: User) -> MailOut:
        return cls(
            id=m.id, sender_name=m.sender_name, sender_org=m.sender_org,
            received_at=m.received_at, subject=m.subject, body=m.body,
            classification=m.classification.value, project_id=m.project_id,
            suggested_project_id=m.suggested_project_id,
            intent=m.intent, confidence=m.confidence.value if m.confidence else None,
            milestone_code=m.milestone_code, note_id=m.note_id, handled=m.handled,
            version=m.version, approved_by=m.approved_by, approved_at=m.approved_at,
            can_review=actor.status.value == "active" and actor.is_admin,
            attachments=[
                AttachmentOut(
                    filename=a.filename, content_type=a.content_type,
                    size_bytes=a.size_bytes, part_index=a.part_index,
                    linked_file_id=a.linked_file_id,
                )
                for a in m.attachments
            ],
            suggestions=[
                MailProjectSuggestionOut(
                    project_id=s.project_id,
                    project_name=s.project_name,
                    confidence=s.confidence.value,
                    reasons=list(s.reasons),
                )
                for s in m.suggestions
            ],
        )


class CountsOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    unclassified: int
    project: int
    unrelated: int
    all: int


class NoteRefOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    note_id: str


class AttachmentSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    part_index: int = Field(ge=0, description="Attachment's position within the source mail.")
    category: str = Field(
        description="One of: original, report, deliverable, source."
    )


class ApproveRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "project_id": "11111111-1111-4111-8111-111111111111",
                "expected_version": 0,
                "attachments": [{"part_index": 0, "category": "deliverable"}],
            }
        },
    )

    project_id: str
    expected_version: int = Field(
        ge=0, description="CAS guard. 0 for a not-yet-decided mail."
    )
    attachments: list[AttachmentSelection] = Field(
        default_factory=list,
        description="Attachments to link now; an empty list is a valid mail-only approval.",
    )


class AttachmentsApproveRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "expected_version": 1,
                "attachments": [{"part_index": 1, "category": "source"}],
            }
        },
    )

    expected_version: int = Field(
        ge=0, description="CAS guard: must equal the mail's current version."
    )
    attachments: list[AttachmentSelection] = Field(
        description="At least one new attachment to link; empty is rejected."
    )


class DismissRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"example": {"expected_version": 0}},
    )

    expected_version: int = Field(
        ge=0, description="CAS guard. 0 for a not-yet-decided mail."
    )


def _selection_inputs(items: list[AttachmentSelection]) -> list[AttachmentSelectionInput]:
    return [AttachmentSelectionInput(part_index=i.part_index, category=i.category) for i in items]


@router.get("/projects/{project_id}/mail", response_model=ListEnvelope[MailOut])
def list_mail(
    project_id: str,
    user: CurrentUser,
    db: Annotated[DbSession, Depends(get_session)],
    status: Literal["unclassified", "project", "unrelated", "all"] = "unclassified",
    offset: int = 0,
    limit: int = 50,
    suggested: Literal["yes", "no"] | None = None,
) -> ListEnvelope[MailOut]:
    if offset < 0:
        raise ProblemError("VALIDATION_FAILED", "offset은 0 이상이어야 합니다.")
    if not (1 <= limit <= 100):
        raise ProblemError("VALIDATION_FAILED", "limit은 1에서 100 사이여야 합니다.")

    items, total = _service(db, user).list_messages(
        project_id, status=status, offset=offset, limit=limit, suggested=suggested
    )
    return collection(
        [MailOut.of(m, user) for m in items],
        total=total,
        has_more=offset + len(items) < total,
    )


@router.get("/projects/{project_id}/mail/counts", response_model=Envelope[CountsOut])
def mail_counts(
    project_id: str, user: CurrentUser, db: Annotated[DbSession, Depends(get_session)]
) -> Envelope[CountsOut]:
    return single(CountsOut(**_service(db, user).counts(project_id)))


@router.get("/mail/{message_id}", response_model=Envelope[MailOut])
def get_mail(
    message_id: str, user: CurrentUser, db: Annotated[DbSession, Depends(get_session)],
    id_encoding: str | None = None,
) -> Envelope[MailOut]:
    return single(
        MailOut.of(_service(db, user).get(_transport_message_id(message_id, id_encoding)), user)
    )


@router.post("/mail/{message_id}/approve", response_model=Envelope[MailOut])
def approve(
    message_id: str,
    request: ApproveRequest,
    user: CurrentUser,
    db: Annotated[DbSession, Depends(get_session)],
    idempotency_key: IdempotencyKey,
    id_encoding: str | None = None,
) -> Envelope[MailOut]:
    message = _service(db, user).approve(
        _transport_message_id(message_id, id_encoding),
        project_id=request.project_id,
        expected_version=request.expected_version,
        attachments=_selection_inputs(request.attachments),
        idem_key=idempotency_key,
    )
    return single(MailOut.of(message, user))


@router.post("/mail/{message_id}/attachments/approve", response_model=Envelope[MailOut])
def attachments_approve(
    message_id: str,
    request: AttachmentsApproveRequest,
    user: CurrentUser,
    db: Annotated[DbSession, Depends(get_session)],
    idempotency_key: IdempotencyKey,
    id_encoding: str | None = None,
) -> Envelope[MailOut]:
    message = _service(db, user).attachments_approve(
        _transport_message_id(message_id, id_encoding),
        expected_version=request.expected_version,
        attachments=_selection_inputs(request.attachments),
        idem_key=idempotency_key,
    )
    return single(MailOut.of(message, user))


@router.post("/mail/{message_id}/dismiss", response_model=Envelope[MailOut])
def dismiss(
    message_id: str,
    request: DismissRequest,
    user: CurrentUser,
    db: Annotated[DbSession, Depends(get_session)],
    idempotency_key: IdempotencyKey,
    id_encoding: str | None = None,
) -> Envelope[MailOut]:
    message = _service(db, user).dismiss(
        _transport_message_id(message_id, id_encoding),
        expected_version=request.expected_version,
        idem_key=idempotency_key,
    )
    return single(MailOut.of(message, user))


@router.get("/mail/{message_id}/attachments/{part_index}")
def download_attachment(
    message_id: str,
    part_index: int,
    user: CurrentUser,
    db: Annotated[DbSession, Depends(get_session)],
    linked_file_id: str | None = None,
    id_encoding: str | None = None,
) -> Response:
    """첨부 하나를 내려받는다.

    블로킹 호출이라 ``def``로 둔다. FastAPI가 스레드풀에서 돌린다.

    ``linked_file_id``는 드라이브가 보낸 file.id다. 값이 있으면 현재
    mailbox_key+UIDL+part의 승인된 첨부가 가진 linked_file_id와 정확히
    일치해야 한다 — 계정을 바꿔 같은 UIDL/part가 재사용된 경우 옛 드라이브
    링크가 새 메일함의 파일을 가리키는 사고를 막는다.
    """

    filename, content_type, payload = _service(db, user).fetch_attachment(
        _transport_message_id(message_id, id_encoding), part_index, linked_file_id=linked_file_id
    )
    safe_type = _sanitize_content_type(content_type)
    quoted = urllib.parse.quote(_sanitize_filename(filename))
    fallback = _filename_fallback(filename)
    return Response(
        content=payload,
        media_type=safe_type,
        headers={
            "content-disposition": (
                f'attachment; filename="{fallback}"; '
                f"filename*=UTF-8''{quoted}"
            ),
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.post("/mail/{message_id}/promote-to-note", response_model=Envelope[NoteRefOut])
def promote_to_note(
    message_id: str, user: CurrentUser, db: Annotated[DbSession, Depends(get_session)],
    id_encoding: str | None = None,
) -> Envelope[NoteRefOut]:
    return single(
        NoteRefOut(
            note_id=_service(db, user).promote_to_note(
                _transport_message_id(message_id, id_encoding)
            )
        )
    )
