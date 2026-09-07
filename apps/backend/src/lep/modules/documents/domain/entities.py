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


@dataclass(frozen=True, slots=True)
class DriveCategorySummary:
    category: DriveCategory
    label: str
    description: str
    count: int
    #: True for 원본문서. New versions go to 산출문서 instead of overwriting.
    read_only: bool
    warning: str | None = None
