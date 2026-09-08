"""Mail HTTP routes."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session as DbSession

from ....common.db import get_session
from ....common.envelope import Envelope, ListEnvelope, collection, single
from ...iam.public import CurrentUser
from ...projects.public import require_project
from ..domain.entities import MailMessage
from ..public import get_mail_service

router = APIRouter(prefix="/api/v1", tags=["mail"])


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
    intent: str | None
    confidence: str | None
    milestone_code: str | None
    note_id: str | None
    handled: bool

    @classmethod
    def of(cls, m: MailMessage) -> MailOut:
        return cls(
            id=m.id, sender_name=m.sender_name, sender_org=m.sender_org,
            received_at=m.received_at, subject=m.subject, body=m.body,
            classification=m.classification.value, project_id=m.project_id,
            intent=m.intent, confidence=m.confidence.value if m.confidence else None,
            milestone_code=m.milestone_code, note_id=m.note_id, handled=m.handled,
        )


class NoteRefOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    note_id: str


@router.get("/projects/{project_id}/mail", response_model=ListEnvelope[MailOut])
def list_mail(
    project_id: str, user: CurrentUser, db: Annotated[DbSession, Depends(get_session)]
) -> ListEnvelope[MailOut]:
    require_project(db, project_id)
    items = get_mail_service().list_messages(project_id)
    return collection([MailOut.of(m) for m in items], total=len(items))


@router.get("/mail/{message_id}", response_model=Envelope[MailOut])
def get_mail(message_id: str, user: CurrentUser) -> Envelope[MailOut]:
    return single(MailOut.of(get_mail_service().get_message(message_id)))


@router.post("/mail/{message_id}/promote-to-note", response_model=Envelope[NoteRefOut])
def promote_to_note(
    message_id: str,
    user: CurrentUser,
    db: Annotated[DbSession, Depends(get_session)],
) -> Envelope[NoteRefOut]:
    service = get_mail_service()
    message = service.get_message(message_id)
    project = require_project(db, message.project_id or "")
    return single(
        NoteRefOut(note_id=service.promote_to_note(message_id, project_code=project.code))
    )


@router.post("/mail/{message_id}/dismiss", response_model=Envelope[MailOut])
def dismiss(message_id: str, user: CurrentUser) -> Envelope[MailOut]:
    return single(MailOut.of(get_mail_service().dismiss(message_id)))
