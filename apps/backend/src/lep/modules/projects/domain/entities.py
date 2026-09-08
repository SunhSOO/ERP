"""Project domain entities.

The domain layer holds no framework imports. ``scripts/check_boundaries.py``
enforces that, which is what lets the SQL adapters in WP-PKD-020 arrive without
touching this file.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ViewRole(StrEnum):
    """Which side of the contract the organisation sits on for this project.

    The mockups switch the whole app between these two. Whether this is a
    permission boundary or a view preference is settled in WP-PKD-021, when real
    sessions exist. Until then it is a view preference only.
    """

    VENDOR = "vendor"
    CLIENT = "client"


class SyncHealth(StrEnum):
    """How an integration is doing for one project.

    Never rendered as colour alone. The UI pairs each value with a glyph and text.
    """

    OK = "ok"
    STALE = "stale"
    MISMATCH = "mismatch"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class Project:
    id: str
    code: str
    name: str
    customer_name: str
    role: ViewRole
    pm_name: str


@dataclass(frozen=True, slots=True)
class ProjectSummary:
    """The home screen card. Every number here belongs to another module and is
    read through that module's ``public`` interface, never from its tables."""

    project_id: str
    wbs_progress_percent: int | None
    schedule_note: str | None
    vault_health: SyncHealth
    vault_note: str
    unclassified_mail_count: int
    vcs_health: SyncHealth
    vcs_note: str
