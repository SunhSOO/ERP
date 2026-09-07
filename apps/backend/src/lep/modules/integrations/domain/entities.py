"""Integrations domain: repository reconciliation, LLM settings, credential state."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class LinkHealth(StrEnum):
    OK = "ok"
    STALE = "stale"
    MISMATCH = "mismatch"
    EXPIRED = "expired"
    NOT_CONFIGURED = "not_configured"


class MismatchKind(StrEnum):
    """The two kinds screen 07 distinguishes."""

    #: Repository activity with no corresponding WBS task.
    UNDEFINED_WORK = "undefined_work"
    #: WBS says done but the pull request is still open.
    STATUS_CONFLICT = "status_conflict"


class ModelState(StrEnum):
    RUNNING = "running"
    STOPPED = "stopped"


class GpuPriority(StrEnum):
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


@dataclass(frozen=True, slots=True)
class VcsStatus:
    project_id: str
    repository: str
    health: LinkHealth
    last_sync_at: datetime
    open_pull_requests: int
    match_rate_percent: int


@dataclass(frozen=True, slots=True)
class Mismatch:
    id: str
    project_id: str
    kind: MismatchKind
    title: str
    detail: str
    #: Which task is implicated, when there is one.
    task_code: str | None
    vcs_ref: str
    resolved: bool = False


@dataclass(frozen=True, slots=True)
class TaskMapping:
    task_code: str | None
    task_title: str
    vcs_ref: str
    task_status: str
    aligned: bool


@dataclass(frozen=True, slots=True)
class LlmServer:
    """The shared GPU box. Isolation is a promise the UI states plainly:
    documents, mail and meeting notes never leave it."""

    name: str
    network_note: str
    gpu_usage_percent: int
    active_model_count: int
    project_count: int


@dataclass(frozen=True, slots=True)
class ProjectModel:
    project_id: str
    project_name: str
    model: str | None
    state: ModelState
    priority: GpuPriority | None
    gpu_share_percent: int | None


@dataclass(frozen=True, slots=True)
class Credential:
    """One integration's configured state for one project.

    Never carries a secret value. Only whether it is configured and healthy.
    Real secret handling waits for WP-PKD-021, when there is a session to
    authorise it.
    """

    kind: str
    label: str
    health: LinkHealth
    detail: str
    #: What the operator must supply before the real adapter can run.
    missing_input: str | None = None
