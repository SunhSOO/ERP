"""Delivery domain: statement of work, tasks, milestones, WBS.

Task status uses the mockup vocabulary, which ADR-016 makes authoritative for this
track. The mapping back to the ERP track's five-step flow lives in that ADR.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class TaskStatus(StrEnum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    DONE = "done"
    #: Detected in the repository but absent from the WBS. No ERP equivalent.
    VCS_ONLY = "vcs_only"


class Confidence(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True, slots=True)
class Milestone:
    id: str
    project_id: str
    code: str
    name: str
    status: TaskStatus
    progress_percent: int
    start: date
    end: date


@dataclass(frozen=True, slots=True)
class Task:
    id: str
    project_id: str
    code: str
    title: str
    milestone_id: str | None
    status: TaskStatus
    start: date
    end: date
    assignee: str | None
    #: Required whenever status is BLOCKED. The UI must show why and who unblocks it.
    blocked_reason: str | None = None
    blocked_owner: str | None = None
    #: Set when the task exists only in the repository.
    vcs_ref: str | None = None


@dataclass(frozen=True, slots=True)
class Statement:
    """과업지시서. The uploaded contract document the tasks are derived from."""

    id: str
    project_id: str
    filename: str
    clause_count: int
    classified_count: int
    analysed: bool


@dataclass(frozen=True, slots=True)
class Clause:
    id: str
    statement_id: str
    article: str
    task_title: str
    category: str
    confidence: Confidence
    #: Where it landed in the WBS, or ``None`` while it still needs a human.
    wbs_mapping: str | None
    promoted_task_id: str | None = None


@dataclass(frozen=True, slots=True)
class ScheduleShift:
    """One row of the impact preview shown before a date change is applied."""

    task_code: str
    task_title: str
    old_end: date
    new_end: date
