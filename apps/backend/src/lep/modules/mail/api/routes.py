"""Mail HTTP routes."""

from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

from ....common.envelope import Envelope, ListEnvelope, collection, single
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
    def of(cls, item: MailMessage) -> MailOut:
        return cls(
            id=item.id,
            sender_name=item.sender_name,
            sender_org=item.sender_org,
            received_at=item.received_at,
            subject=item.subject,
            body=item.body,
            classification=item.classification.value,
            project_id=item.project_id,
            intent=item.intent,
            confidence=item.confidence.value if item.confidence else None,
            milestone_code=item.milestone_code,
            note_id=item.note_id,
            handled=item.handled,
        )


class ShiftOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_code: str
    task_title: str
    old_end: date
    new_end: date


class MailDetailOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: MailOut
    #: Empty unless the message implies a date change.
    schedule_preview: list[ShiftOut]


class NoteRefOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    note_id: str


@router.get("/projects/{project_id}/mail", response_model=ListEnvelope[MailOut])
async def list_mail(project_id: str) -> ListEnvelope[MailOut]:
    items = get_mail_service().list_messages(project_id)
    return collection([MailOut.of(item) for item in items], total=len(items))


@router.get("/mail/{message_id}", response_model=Envelope[MailDetailOut])
async def get_mail(message_id: str) -> Envelope[MailDetailOut]:
    service = get_mail_service()
    message = service.get_message(message_id)
    preview: list[ShiftOut] = []
    if message.milestone_code and not message.handled:
        preview = [
            ShiftOut(
                task_code=shift.task_code,
                task_title=shift.task_title,
                old_end=shift.old_end,
                new_end=shift.new_end,
            )
            for shift in service.preview_schedule_impact(message_id)
        ]
    return single(MailDetailOut(message=MailOut.of(message), schedule_preview=preview))


@router.post("/mail/{message_id}/promote-to-note", response_model=Envelope[NoteRefOut])
async def promote_to_note(message_id: str) -> Envelope[NoteRefOut]:
    return single(NoteRefOut(note_id=get_mail_service().promote_to_note(message_id)))


@router.post("/mail/{message_id}/apply-to-wbs", response_model=ListEnvelope[ShiftOut])
async def apply_to_wbs(message_id: str) -> ListEnvelope[ShiftOut]:
    shifts = get_mail_service().apply_to_wbs(message_id)
    return collection(
        [
            ShiftOut(
                task_code=shift.task_code,
                task_title=shift.task_title,
                old_end=shift.old_end,
                new_end=shift.new_end,
            )
            for shift in shifts
        ],
        total=len(shifts),
    )


@router.post("/mail/{message_id}/dismiss", response_model=Envelope[MailOut])
async def dismiss(message_id: str) -> Envelope[MailOut]:
    return single(MailOut.of(get_mail_service().dismiss(message_id)))
