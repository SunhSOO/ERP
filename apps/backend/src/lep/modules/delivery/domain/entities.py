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
    #: 절의 본문 전체. 화면의 상세 보기와 재분류가 쓴다.
    body: str = ""
    #: 십진 번호에서 온 위치. 화면이 트리로 그린다.
    level: int = 1
    parent: str | None = None
    #: 수행해서 완료할 수 있는 일인지.
    actionable: bool = False
    #: 분류기의 근거, 또는 분류하지 못한 사유.
    classified_reason: str | None = None
    #: 어느 분류기가 답했는지. 픽스처와 실제 모델을 구분한다.
    classified_by: str | None = None


@dataclass(frozen=True, slots=True)
class ScheduleShift:
    """One row of the impact preview shown before a date change is applied."""

    task_code: str
    task_title: str
    old_end: date
    new_end: date


@dataclass(frozen=True, slots=True)
class ClassificationRun:
    """분류를 한 번 돌린 결과.

    몇 개를 분류했는지와 몇 개가 실패했는지를 따로 센다. 둘을 합쳐 "완료"라고
    말하면 모델이 절반을 못 읽은 것을 사용자가 알 수 없다.
    """

    #: 어느 분류기가 답했는지. 픽스처면 아무것도 분류하지 않았다는 뜻이다.
    classifier: str
    total: int
    classified: int
    failed: int
    #: 실제 어댑터를 요청했는데 쓰지 못한 사유. 조용히 대체하지 않는다.
    unavailable_reason: str | None = None
