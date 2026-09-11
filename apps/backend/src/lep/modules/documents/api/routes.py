"""Document pipeline and drive HTTP routes."""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session as DbSession

from ....common.db import get_session
from ....common.envelope import Envelope, ListEnvelope, collection, single
from ....common.pagination import DEFAULT_LIMIT, MAX_LIMIT, encode_cursor, paginate
from ...iam.public import CurrentUser
from ..domain.entities import (
    Document,
    DriveCategory,
    DriveCategorySummary,
    DriveFile,
)
from ..public import get_document_service

router = APIRouter(prefix="/api/v1", tags=["documents"])


class DocumentOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    stage: int
    state: str
    converter: str
    author: str
    updated_at: datetime
    markdown: str
    failure_reason: str | None

    @classmethod
    def of(cls, item: Document) -> DocumentOut:
        return cls(
            id=item.id,
            title=item.title,
            stage=int(item.stage),
            state=item.state.value,
            converter=item.converter,
            author=item.author,
            updated_at=item.updated_at,
            markdown=item.markdown,
            failure_reason=item.failure_reason,
        )


class DriveFileOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    category: str
    origin: str
    size_bytes: int
    modified: date
    warning: str | None
    source_mail_id: str | None = None
    source_part_index: int | None = None
    source_kind: str | None = None
    sha256: str | None = None

    @classmethod
    def of(cls, item: DriveFile) -> DriveFileOut:
        return cls(
            id=item.id,
            name=item.name,
            category=item.category.value,
            origin=item.origin,
            size_bytes=item.size_bytes,
            modified=item.modified,
            warning=item.warning,
            source_mail_id=item.source_mail_id,
            source_part_index=item.source_part_index,
            source_kind=item.source_kind,
            sha256=item.sha256,
        )


class DriveCategoryOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: str
    label: str
    description: str
    count: int
    read_only: bool
    warning: str | None

    @classmethod
    def of(cls, item: DriveCategorySummary) -> DriveCategoryOut:
        return cls(
            category=item.category.value,
            label=item.label,
            description=item.description,
            count=item.count,
            read_only=item.read_only,
            warning=item.warning,
        )


@router.get("/projects/{project_id}/documents", response_model=ListEnvelope[DocumentOut])
async def list_documents(
    project_id: str,
    user: CurrentUser,
    db: Annotated[DbSession, Depends(get_session)],
) -> ListEnvelope[DocumentOut]:
    items = get_document_service().list_documents(db, project_id)
    return collection([DocumentOut.of(item) for item in items], total=len(items))


@router.get("/documents/{document_id}", response_model=Envelope[DocumentOut])
async def get_document(document_id: str, user: CurrentUser) -> Envelope[DocumentOut]:
    return single(DocumentOut.of(get_document_service().get_document(document_id)))


@router.post("/documents/{document_id}/convert", response_model=Envelope[DocumentOut])
async def convert_document(document_id: str, user: CurrentUser) -> Envelope[DocumentOut]:
    return single(DocumentOut.of(get_document_service().convert(document_id)))


@router.post("/documents/{document_id}/retry", response_model=Envelope[DocumentOut])
async def retry_document(document_id: str, user: CurrentUser) -> Envelope[DocumentOut]:
    return single(DocumentOut.of(get_document_service().retry(document_id)))


@router.get("/projects/{project_id}/drive", response_model=ListEnvelope[DriveCategoryOut])
def get_drive(
    project_id: str,
    user: CurrentUser,
    db: Annotated[DbSession, Depends(get_session)],
) -> ListEnvelope[DriveCategoryOut]:
    items = get_document_service().drive_summary(db, project_id, actor=user)
    return collection([DriveCategoryOut.of(item) for item in items], total=len(items))


@router.get("/projects/{project_id}/drive/files", response_model=ListEnvelope[DriveFileOut])
def list_drive_files(
    project_id: str,
    user: CurrentUser,
    db: Annotated[DbSession, Depends(get_session)],
    category: Annotated[DriveCategory | None, Query()] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
) -> ListEnvelope[DriveFileOut]:
    items = get_document_service().list_files(db, project_id, category, actor=user)
    page = paginate(items, cursor=encode_cursor(offset), limit=limit)
    return collection(
        [DriveFileOut.of(item) for item in page.items],
        next_cursor=page.next_cursor,
        has_more=page.has_more,
        total=page.total,
    )
