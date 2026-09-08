"""Knowledge HTTP routes: vault, notes, meetings."""

from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

from ....common.envelope import Envelope, ListEnvelope, collection, single
from ..application.services import ApplyMode, ApplyPreview
from ..domain.entities import ActionItem, Decision, Meeting, Note, VaultStatus
from ..public import get_knowledge_service

router = APIRouter(prefix="/api/v1", tags=["knowledge"])


class VaultStatusOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: str
    health: str
    last_sync_at: datetime
    note_count: int
    vault_path: str

    @classmethod
    def of(cls, item: VaultStatus) -> VaultStatusOut:
        return cls(
            project_id=item.project_id,
            health=item.health.value,
            last_sync_at=item.last_sync_at,
            note_count=item.note_count,
            vault_path=item.vault_path,
        )


class BacklinkOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target: str
    label: str


class NoteOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    source: str
    note_count: int
    updated_at: date | None
    body: str
    backlinks: list[BacklinkOut]
    warning: str | None
    task_code: str | None

    @classmethod
    def of(cls, item: Note) -> NoteOut:
        return cls(
            id=item.id,
            title=item.title,
            source=item.source.value,
            note_count=item.note_count,
            updated_at=item.updated_at,
            body=item.body,
            backlinks=[BacklinkOut(target=b.target, label=b.label) for b in item.backlinks],
            warning=item.warning,
            task_code=item.task_code,
        )


class MeetingOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    code: str
    title: str
    held_at: datetime
    attendees: list[str]
    apply_status: str
    pending_count: int

    @classmethod
    def of(cls, item: Meeting) -> MeetingOut:
        return cls(
            id=item.id,
            code=item.code,
            title=item.title,
            held_at=item.held_at,
            attendees=list(item.attendees),
            apply_status=item.apply_status.value,
            pending_count=item.pending_count,
        )


class DecisionOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    ordinal: int
    text: str
    applied: bool
    milestone_code: str | None
    new_end: date | None

    @classmethod
    def of(cls, item: Decision) -> DecisionOut:
        return cls(
            id=item.id,
            ordinal=item.ordinal,
            text=item.text,
            applied=item.applied,
            milestone_code=item.milestone_code,
            new_end=item.new_end,
        )


class ActionItemOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    text: str
    owner: str | None
    due: date | None
    task_created: bool
    needs_approval: bool

    @classmethod
    def of(cls, item: ActionItem) -> ActionItemOut:
        return cls(
            id=item.id,
            text=item.text,
            owner=item.owner,
            due=item.due,
            task_created=item.task_created,
            needs_approval=item.needs_approval,
        )


class ShiftOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_code: str
    task_title: str
    old_end: date
    new_end: date


class ApplyPreviewOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    milestone_code: str | None
    new_end: date | None
    shifts: list[ShiftOut]

    @classmethod
    def of(cls, item: ApplyPreview) -> ApplyPreviewOut:
        return cls(
            milestone_code=item.milestone_code,
            new_end=item.new_end,
            shifts=[
                ShiftOut(
                    task_code=shift.task_code,
                    task_title=shift.task_title,
                    old_end=shift.old_end,
                    new_end=shift.new_end,
                )
                for shift in item.shifts
            ],
        )


class ApplyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: ApplyMode


class MeetingDetailOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    meeting: MeetingOut
    decisions: list[DecisionOut]
    action_items: list[ActionItemOut]
    preview: ApplyPreviewOut


@router.get("/projects/{project_id}/vault", response_model=Envelope[VaultStatusOut])
async def get_vault(project_id: str) -> Envelope[VaultStatusOut]:
    return single(VaultStatusOut.of(get_knowledge_service().get_vault_status(project_id)))


@router.post("/projects/{project_id}/vault/sync", response_model=Envelope[VaultStatusOut])
async def resync_vault(project_id: str) -> Envelope[VaultStatusOut]:
    return single(VaultStatusOut.of(get_knowledge_service().resync(project_id)))


@router.get("/projects/{project_id}/notes", response_model=ListEnvelope[NoteOut])
async def list_notes(project_id: str) -> ListEnvelope[NoteOut]:
    items = get_knowledge_service().list_notes(project_id)
    return collection([NoteOut.of(item) for item in items], total=len(items))


@router.get("/notes/{note_id}", response_model=Envelope[NoteOut])
async def get_note(note_id: str) -> Envelope[NoteOut]:
    return single(NoteOut.of(get_knowledge_service().get_note(note_id)))


@router.get("/projects/{project_id}/meetings", response_model=ListEnvelope[MeetingOut])
async def list_meetings(project_id: str) -> ListEnvelope[MeetingOut]:
    items = get_knowledge_service().list_meetings(project_id)
    return collection([MeetingOut.of(item) for item in items], total=len(items))


@router.get("/meetings/{meeting_id}", response_model=Envelope[MeetingDetailOut])
async def get_meeting(meeting_id: str) -> Envelope[MeetingDetailOut]:
    service = get_knowledge_service()
    return single(
        MeetingDetailOut(
            meeting=MeetingOut.of(service.get_meeting(meeting_id)),
            decisions=[DecisionOut.of(item) for item in service.list_decisions(meeting_id)],
            action_items=[
                ActionItemOut.of(item) for item in service.list_action_items(meeting_id)
            ],
            preview=ApplyPreviewOut.of(service.preview_apply(meeting_id)),
        )
    )


@router.post("/meetings/{meeting_id}/apply", response_model=Envelope[ApplyPreviewOut])
async def apply_meeting(meeting_id: str, request: ApplyRequest) -> Envelope[ApplyPreviewOut]:
    return single(
        ApplyPreviewOut.of(get_knowledge_service().apply(meeting_id, request.mode))
    )
