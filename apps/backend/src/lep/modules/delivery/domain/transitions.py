"""Pure task transition and edit validation rules (ADR-016 mockup vocabulary).

The rule this module defends: the transition graph is closed and deterministic,
so neither a bad status jump nor a blank blocker reason/owner can slip through
before a service ever touches the database.
"""

from __future__ import annotations

from datetime import date

from lep.common.problems import ProblemError

from .entities import TaskStatus

_GRAPH: dict[TaskStatus, tuple[TaskStatus, ...]] = {
    TaskStatus.PLANNED: (TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED),
    TaskStatus.IN_PROGRESS: (TaskStatus.BLOCKED, TaskStatus.DONE),
    TaskStatus.BLOCKED: (TaskStatus.PLANNED, TaskStatus.IN_PROGRESS),
    TaskStatus.DONE: (TaskStatus.IN_PROGRESS,),
    TaskStatus.VCS_ONLY: (),
}

_TITLE_MAX_LENGTH = 300


def allowed_transitions(status: TaskStatus) -> tuple[TaskStatus, ...]:
    return _GRAPH[status]


def validate_transition(
    current: TaskStatus,
    target: TaskStatus,
    *,
    blocked_reason: str | None = None,
    blocked_owner: str | None = None,
) -> None:
    if target not in allowed_transitions(current):
        raise ProblemError("STATE_CONFLICT", "현재 상태에서는 처리할 수 없습니다.")

    if target is TaskStatus.BLOCKED:
        if blocked_reason is None or not blocked_reason.strip():
            raise ProblemError("VALIDATION_FAILED", "차단 사유를 입력해 주세요.")
        if blocked_owner is None or not blocked_owner.strip():
            raise ProblemError("VALIDATION_FAILED", "차단 담당자를 입력해 주세요.")


def validate_task_edit(title: str, start: date, end: date) -> str:
    stripped_title = title.strip()
    if not (1 <= len(stripped_title) <= _TITLE_MAX_LENGTH):
        raise ProblemError("VALIDATION_FAILED", "제목은 1자 이상 300자 이하로 입력해 주세요.")
    if end < start:
        raise ProblemError("VALIDATION_FAILED", "종료일은 시작일보다 빠를 수 없습니다.")
    return stripped_title
