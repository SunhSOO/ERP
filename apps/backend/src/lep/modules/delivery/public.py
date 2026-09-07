"""Stable public interface for the delivery module.

Knowledge (screen 08) and integrations (screen 07) both need to change the
schedule. They do it through here, never by touching delivery's data.
"""

from __future__ import annotations

from datetime import date
from functools import lru_cache

from .application.services import DeliveryService
from .domain.entities import ScheduleShift
from .infrastructure.memory import InMemoryDeliveryRepository

__all__ = [
    "ScheduleShift",
    "adopt_vcs_task",
    "get_delivery_service",
    "preview_milestone_shift",
    "shift_milestone",
    "find_milestone_id_by_code",
]


@lru_cache(maxsize=1)
def get_delivery_service() -> DeliveryService:
    return DeliveryService(InMemoryDeliveryRepository())


def find_milestone_id_by_code(project_id: str, code: str) -> str | None:
    """Resolve "M3" to a milestone ID. Screens 06 and 08 refer to milestones by code."""

    for milestone in get_delivery_service().list_milestones(project_id):
        if milestone.code == code:
            return milestone.id
    return None


def preview_milestone_shift(milestone_id: str, new_end: date) -> list[ScheduleShift]:
    return get_delivery_service().preview_milestone_shift(milestone_id, new_end)


def shift_milestone(milestone_id: str, new_end: date) -> list[ScheduleShift]:
    return get_delivery_service().shift_milestone(milestone_id, new_end)


def adopt_vcs_task(task_code: str, milestone_id: str | None = None) -> str:
    """Promote a repository-only item to a WBS task and return its code."""

    return get_delivery_service().adopt_vcs_task(task_code, milestone_id).code
