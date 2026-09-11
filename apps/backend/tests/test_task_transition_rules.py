"""Pure task transition and edit validation rules (ADR-016 mockup vocabulary).

The rule the tests defend: the transition graph is closed and deterministic, so
neither a bad status jump nor a blank blocker reason/owner can slip through
before a service ever touches the database.
"""

from __future__ import annotations

from datetime import date

import pytest

from lep.common.problems import ProblemError
from lep.modules.delivery.domain.entities import TaskStatus
from lep.modules.delivery.domain.transitions import (
    allowed_transitions,
    validate_task_edit,
    validate_transition,
)

# --- allowed_transitions --------------------------------------------------


def test_allowed_transitions_from_planned() -> None:
    assert allowed_transitions(TaskStatus.PLANNED) == (
        TaskStatus.IN_PROGRESS,
        TaskStatus.BLOCKED,
    )


def test_allowed_transitions_from_in_progress() -> None:
    assert allowed_transitions(TaskStatus.IN_PROGRESS) == (
        TaskStatus.BLOCKED,
        TaskStatus.DONE,
    )


def test_allowed_transitions_from_blocked() -> None:
    assert allowed_transitions(TaskStatus.BLOCKED) == (
        TaskStatus.PLANNED,
        TaskStatus.IN_PROGRESS,
    )


def test_allowed_transitions_from_done() -> None:
    assert allowed_transitions(TaskStatus.DONE) == (TaskStatus.IN_PROGRESS,)


def test_allowed_transitions_from_vcs_only_is_empty() -> None:
    assert allowed_transitions(TaskStatus.VCS_ONLY) == ()


def test_allowed_transitions_is_immutable_tuple() -> None:
    result = allowed_transitions(TaskStatus.PLANNED)
    assert isinstance(result, tuple)


def test_allowed_transitions_deterministic_across_calls() -> None:
    assert allowed_transitions(TaskStatus.PLANNED) == allowed_transitions(TaskStatus.PLANNED)


# --- validate_transition: valid edges -------------------------------------


def test_valid_transition_planned_to_in_progress() -> None:
    validate_transition(TaskStatus.PLANNED, TaskStatus.IN_PROGRESS)


def test_valid_transition_planned_to_blocked_requires_reason_and_owner() -> None:
    validate_transition(
        TaskStatus.PLANNED,
        TaskStatus.BLOCKED,
        blocked_reason="waiting on client",
        blocked_owner="pm@example.invalid",
    )


def test_valid_transition_in_progress_to_blocked() -> None:
    validate_transition(
        TaskStatus.IN_PROGRESS,
        TaskStatus.BLOCKED,
        blocked_reason="waiting on vendor",
        blocked_owner="lead@example.invalid",
    )


def test_valid_transition_in_progress_to_done() -> None:
    validate_transition(TaskStatus.IN_PROGRESS, TaskStatus.DONE)


def test_valid_transition_blocked_to_planned() -> None:
    validate_transition(TaskStatus.BLOCKED, TaskStatus.PLANNED)


def test_valid_transition_blocked_to_in_progress() -> None:
    validate_transition(TaskStatus.BLOCKED, TaskStatus.IN_PROGRESS)


def test_valid_transition_done_to_in_progress() -> None:
    validate_transition(TaskStatus.DONE, TaskStatus.IN_PROGRESS)


# --- validate_transition: invalid edges -> STATE_CONFLICT (409) ----------


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (TaskStatus.PLANNED, TaskStatus.DONE),
        (TaskStatus.PLANNED, TaskStatus.PLANNED),
        (TaskStatus.IN_PROGRESS, TaskStatus.PLANNED),
        (TaskStatus.IN_PROGRESS, TaskStatus.IN_PROGRESS),
        (TaskStatus.BLOCKED, TaskStatus.DONE),
        (TaskStatus.BLOCKED, TaskStatus.BLOCKED),
        (TaskStatus.DONE, TaskStatus.PLANNED),
        (TaskStatus.DONE, TaskStatus.BLOCKED),
        (TaskStatus.DONE, TaskStatus.DONE),
        (TaskStatus.PLANNED, TaskStatus.VCS_ONLY),
        (TaskStatus.IN_PROGRESS, TaskStatus.VCS_ONLY),
        (TaskStatus.BLOCKED, TaskStatus.VCS_ONLY),
        (TaskStatus.DONE, TaskStatus.VCS_ONLY),
        (TaskStatus.VCS_ONLY, TaskStatus.PLANNED),
        (TaskStatus.VCS_ONLY, TaskStatus.IN_PROGRESS),
        (TaskStatus.VCS_ONLY, TaskStatus.BLOCKED),
        (TaskStatus.VCS_ONLY, TaskStatus.DONE),
        (TaskStatus.VCS_ONLY, TaskStatus.VCS_ONLY),
    ],
)
def test_invalid_transition_raises_state_conflict(
    current: TaskStatus, target: TaskStatus
) -> None:
    with pytest.raises(ProblemError) as excinfo:
        validate_transition(current, target)
    assert excinfo.value.code == "STATE_CONFLICT"
    assert excinfo.value.status == 409


def test_same_state_transition_is_always_invalid_even_when_blocked() -> None:
    with pytest.raises(ProblemError) as excinfo:
        validate_transition(
            TaskStatus.BLOCKED,
            TaskStatus.BLOCKED,
            blocked_reason="still waiting",
            blocked_owner="pm@example.invalid",
        )
    assert excinfo.value.code == "STATE_CONFLICT"


# --- validate_transition: blocked metadata -> VALIDATION_FAILED (422) ----


def test_transition_to_blocked_missing_reason_and_owner_raises_validation_failed() -> None:
    with pytest.raises(ProblemError) as excinfo:
        validate_transition(TaskStatus.PLANNED, TaskStatus.BLOCKED)
    assert excinfo.value.code == "VALIDATION_FAILED"
    assert excinfo.value.status == 422


def test_transition_to_blocked_missing_owner_raises_validation_failed() -> None:
    with pytest.raises(ProblemError) as excinfo:
        validate_transition(
            TaskStatus.PLANNED, TaskStatus.BLOCKED, blocked_reason="waiting on client"
        )
    assert excinfo.value.code == "VALIDATION_FAILED"


def test_transition_to_blocked_missing_reason_raises_validation_failed() -> None:
    with pytest.raises(ProblemError) as excinfo:
        validate_transition(
            TaskStatus.PLANNED, TaskStatus.BLOCKED, blocked_owner="pm@example.invalid"
        )
    assert excinfo.value.code == "VALIDATION_FAILED"


def test_transition_to_blocked_blank_reason_raises_validation_failed() -> None:
    with pytest.raises(ProblemError) as excinfo:
        validate_transition(
            TaskStatus.PLANNED,
            TaskStatus.BLOCKED,
            blocked_reason="   ",
            blocked_owner="pm@example.invalid",
        )
    assert excinfo.value.code == "VALIDATION_FAILED"


def test_transition_to_blocked_blank_owner_raises_validation_failed() -> None:
    with pytest.raises(ProblemError) as excinfo:
        validate_transition(
            TaskStatus.PLANNED,
            TaskStatus.BLOCKED,
            blocked_reason="waiting on client",
            blocked_owner="   ",
        )
    assert excinfo.value.code == "VALIDATION_FAILED"


def test_transition_to_blocked_succeeds_with_whitespace_padded_reason_and_owner() -> None:
    validate_transition(
        TaskStatus.PLANNED,
        TaskStatus.BLOCKED,
        blocked_reason="  waiting on client  ",
        blocked_owner="  pm@example.invalid  ",
    )


def test_transition_not_to_blocked_ignores_blocked_metadata_even_if_blank() -> None:
    validate_transition(
        TaskStatus.PLANNED,
        TaskStatus.IN_PROGRESS,
        blocked_reason=None,
        blocked_owner=None,
    )


def test_invalid_transition_target_checked_before_blocked_metadata_state_conflict_wins() -> None:
    # planned -> done is not a valid edge at all, regardless of blocked fields
    with pytest.raises(ProblemError) as excinfo:
        validate_transition(
            TaskStatus.PLANNED, TaskStatus.DONE, blocked_reason="", blocked_owner=""
        )
    assert excinfo.value.code == "STATE_CONFLICT"


# --- validate_task_edit ----------------------------------------------------


def test_validate_task_edit_valid_returns_stripped_title() -> None:
    title = validate_task_edit("  Build the report  ", date(2026, 1, 1), date(2026, 1, 31))
    assert title == "Build the report"


def test_validate_task_edit_equal_start_and_end_is_valid() -> None:
    title = validate_task_edit("Same day task", date(2026, 1, 1), date(2026, 1, 1))
    assert title == "Same day task"


def test_validate_task_edit_blank_title_raises_validation_failed() -> None:
    with pytest.raises(ProblemError) as excinfo:
        validate_task_edit("   ", date(2026, 1, 1), date(2026, 1, 31))
    assert excinfo.value.code == "VALIDATION_FAILED"
    assert excinfo.value.status == 422


def test_validate_task_edit_empty_title_raises_validation_failed() -> None:
    with pytest.raises(ProblemError) as excinfo:
        validate_task_edit("", date(2026, 1, 1), date(2026, 1, 31))
    assert excinfo.value.code == "VALIDATION_FAILED"


def test_validate_task_edit_title_over_300_chars_raises_validation_failed() -> None:
    with pytest.raises(ProblemError) as excinfo:
        validate_task_edit("a" * 301, date(2026, 1, 1), date(2026, 1, 31))
    assert excinfo.value.code == "VALIDATION_FAILED"


def test_validate_task_edit_title_exactly_300_chars_is_valid() -> None:
    title = validate_task_edit("a" * 300, date(2026, 1, 1), date(2026, 1, 31))
    assert title == "a" * 300


def test_validate_task_edit_end_before_start_raises_validation_failed() -> None:
    with pytest.raises(ProblemError) as excinfo:
        validate_task_edit("Task", date(2026, 2, 1), date(2026, 1, 1))
    assert excinfo.value.code == "VALIDATION_FAILED"
