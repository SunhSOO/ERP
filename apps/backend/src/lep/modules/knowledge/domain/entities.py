"""Knowledge domain: Obsidian vault notes, meetings, decisions, action items."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum


class SyncHealth(StrEnum):
    OK = "ok"
    STALE = "stale"
    FAILED = "failed"


class NoteSource(StrEnum):
    MEETING = "meeting"
    STATEMENT = "statement"
    MAIL = "mail"
    MANUAL = "manual"


class ApplyStatus(StrEnum):
    """Whether a meeting's outcomes have reached the vault and the WBS."""

    PENDING = "pending"
    APPLIED = "applied"
    DISMISSED = "dismissed"


@dataclass(frozen=True, slots=True)
class VaultStatus:
    project_id: str
    health: SyncHealth
    last_sync_at: datetime
    note_count: int
    #: Where the vault lives. Empty until WP-PKD-032 wires a real path.
    vault_path: str


@dataclass(frozen=True, slots=True)
class Backlink:
    target: str
    label: str


@dataclass(frozen=True, slots=True)
class Note:
    id: str
    project_id: str
    title: str
    source: NoteSource
    note_count: int
    updated_at: date | None
    body: str
    backlinks: list[Backlink] = field(default_factory=list)
    #: Shown when the note carries an unresolved tag, e.g. 미확정.
    warning: str | None = None
    #: Which task this note documents, if any.
    task_code: str | None = None


@dataclass(frozen=True, slots=True)
class Decision:
    id: str
    meeting_id: str
    ordinal: int
    text: str
    applied: bool
    #: Set when the decision implies a schedule change.
    milestone_code: str | None = None
    new_end: date | None = None


@dataclass(frozen=True, slots=True)
class ActionItem:
    id: str
    meeting_id: str
    text: str
    owner: str | None
    due: date | None
    #: True once a real task exists. "완료"는 실제 결과가 있을 때만 쓴다.
    task_created: bool
    needs_approval: bool


@dataclass(frozen=True, slots=True)
class Meeting:
    id: str
    project_id: str
    code: str
    title: str
    held_at: datetime
    attendees: list[str]
    apply_status: ApplyStatus
    pending_count: int


@dataclass(frozen=True, slots=True)
class StatementSection:
    """과업지시서에서 규칙으로 뽑아낸 절 하나.

    delivery 모듈이 문서를 쪼개고 이 형태로 넘긴다. knowledge는 문서 형식을
    모르고, delivery는 파일 시스템을 모른다. 둘 사이의 계약이 이것 하나다.
    """

    number: str
    title: str
    body: str
    level: int
    parent: str | None
