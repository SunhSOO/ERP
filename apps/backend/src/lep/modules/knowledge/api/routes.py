"""Knowledge HTTP routes: the project vault and its notes.

Meetings are not seeded. A project has none until someone records one, and the
screen shows an empty state rather than invented rows. Meeting capture is its
own work package.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session as DbSession

from ....common.db import get_session
from ....common.envelope import Envelope, ListEnvelope, collection, single
from ....common.problems import not_found
from ...iam.public import CurrentUser
from ...projects.public import require_project
from ..domain.entities import Note, VaultStatus
from ..public import get_vault

router = APIRouter(prefix="/api/v1", tags=["knowledge"])


class VaultStatusOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: str
    health: str
    last_sync_at: datetime
    note_count: int
    vault_path: str

    @classmethod
    def of(cls, v: VaultStatus) -> VaultStatusOut:
        return cls(
            project_id=v.project_id, health=v.health.value, last_sync_at=v.last_sync_at,
            note_count=v.note_count, vault_path=v.vault_path,
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
    def of(cls, n: Note) -> NoteOut:
        return cls(
            id=n.id, title=n.title, source=n.source.value, note_count=n.note_count,
            updated_at=n.updated_at, body=n.body,
            backlinks=[BacklinkOut(target=b.target, label=b.label) for b in n.backlinks],
            warning=n.warning, task_code=n.task_code,
        )


class CreateNoteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    body: str = Field(default="", max_length=200_000)
    folder: str = Field(default="notes", max_length=40)


@router.get("/projects/{project_id}/vault", response_model=Envelope[VaultStatusOut])
def get_vault_status(
    project_id: str, user: CurrentUser, db: Annotated[DbSession, Depends(get_session)]
) -> Envelope[VaultStatusOut]:
    project = require_project(db, project_id)
    return single(VaultStatusOut.of(get_vault().status(project.id, project.code)))


@router.post("/projects/{project_id}/vault/sync", response_model=Envelope[VaultStatusOut])
def resync_vault(
    project_id: str, user: CurrentUser, db: Annotated[DbSession, Depends(get_session)]
) -> Envelope[VaultStatusOut]:
    project = require_project(db, project_id)
    vault = get_vault()
    vault.ensure(project.code)
    return single(VaultStatusOut.of(vault.resync(project.id, project.code)))


@router.get("/projects/{project_id}/notes", response_model=ListEnvelope[NoteOut])
def list_notes(
    project_id: str, user: CurrentUser, db: Annotated[DbSession, Depends(get_session)]
) -> ListEnvelope[NoteOut]:
    project = require_project(db, project_id)
    items = get_vault().list_notes(project.id, project.code)
    return collection([NoteOut.of(n) for n in items], total=len(items))


@router.post("/projects/{project_id}/notes", response_model=Envelope[NoteOut], status_code=201)
def create_note(
    project_id: str,
    request: CreateNoteRequest,
    user: CurrentUser,
    db: Annotated[DbSession, Depends(get_session)],
) -> Envelope[NoteOut]:
    project = require_project(db, project_id)
    vault = get_vault()
    stem = vault.create_note(
        project.code, title=request.title, body=request.body, folder=request.folder
    )
    created = next(
        (n for n in vault.list_notes(project.id, project.code) if n.title == stem), None
    )
    if created is None:
        raise not_found("노트를 만들었지만 다시 읽지 못했습니다.")
    return single(NoteOut.of(created))


@router.get("/projects/{project_id}/notes/{note_id}", response_model=Envelope[NoteOut])
def get_note(
    project_id: str,
    note_id: str,
    user: CurrentUser,
    db: Annotated[DbSession, Depends(get_session)],
) -> Envelope[NoteOut]:
    project = require_project(db, project_id)
    note = get_vault().get_note(project.id, project.code, note_id)
    if note is None:
        raise not_found(f"노트를 찾을 수 없습니다: {note_id}")
    return single(NoteOut.of(note))
