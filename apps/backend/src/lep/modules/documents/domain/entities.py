"""Documents domain: the md-to-hwpx pipeline and the project drive."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import IntEnum, StrEnum


class PipelineStage(IntEnum):
    """The five stages the mockup draws. Ordered, so the UI can render progress."""

    DRAFT = 1
    QUEUED = 2
    GENERATING = 3
    REVIEW = 4
    SENT = 5


class PipelineState(StrEnum):
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class DriveCategory(StrEnum):
    """The four-way split on screen 10."""

    ORIGINAL = "original"
    REPORT = "report"
    DELIVERABLE = "deliverable"
    SOURCE = "source"


@dataclass(frozen=True, slots=True)
class Document:
    id: str
    project_id: str
    title: str
    stage: PipelineStage
    state: PipelineState
    converter: str
    author: str
    updated_at: datetime
    markdown: str
    #: Set when the conversion failed. Shown with a retry action, never hidden.
    failure_reason: str | None = None


@dataclass(frozen=True, slots=True)
class DriveFile:
    id: str
    project_id: str
    name: str
    category: DriveCategory
    #: Where the file came from: 계약 모듈, 메일 첨부, 지식화됨, 고객 제공.
    origin: str
    size_bytes: int
    modified: date
    warning: str | None = None
    #: Set only for approved mail attachment references (ADR-021). ``source_mail_id``
    #: is the mail message_id, not a documents-owned identifier.
    source_mail_id: str | None = None
    source_part_index: int | None = None
    source_kind: str | None = None
    sha256: str | None = None


@dataclass(frozen=True, slots=True)
class MailAttachmentLinkInput:
    """One approved attachment to connect to the drive (ADR-021).

    ``category`` accepts all four ``DriveCategory`` values, including
    ``original`` — unlike ``DocumentService.add_file``, this path records an
    approved reference rather than accepting a direct upload.
    """

    part_index: int
    name: str
    content_type: str
    size_bytes: int
    sha256: str
    category: str


@dataclass(frozen=True, slots=True)
class MailAttachmentLinkRef:
    id: str
    part_index: int


@dataclass(frozen=True, slots=True)
class DriveCategorySummary:
    category: DriveCategory
    label: str
    description: str
    count: int
    #: True for 원본문서. New versions go to 산출문서 instead of overwriting.
    read_only: bool
    warning: str | None = None
