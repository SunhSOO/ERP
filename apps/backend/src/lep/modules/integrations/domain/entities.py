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


class LlmRuntimeStatus(StrEnum):
    """What a read-only probe of the configured inference server found.

    Never inferred from installed-but-not-loaded models: ``CONNECTED`` and
    ``DEGRADED`` both require an actual response from the server.
    """

    #: Both the model list and the running-models probe answered.
    CONNECTED = "connected"
    #: The model list answered but the running-models probe did not.
    DEGRADED = "degraded"
    #: Neither probe could be reached, timed out, or returned an unreadable body.
    UNAVAILABLE = "unavailable"
    #: No real adapter selected; nothing was contacted.
    FIXTURE = "fixture"
    #: A real adapter was requested but its configuration is incomplete.
    NOT_CONFIGURED = "not_configured"


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
class LlmRuntimeSnapshot:
    """A read-only status read of the configured inference server.

    ``gpu_usage_percent`` is always ``None``: neither the OpenAI-compatible
    ``/models`` endpoint nor Ollama's ``/api/ps`` reports GPU utilization, so
    this is never fabricated as zero. ``active_model_count`` counts only
    models the probe found *loaded* (``/api/ps``); an installed-but-unloaded
    model is not running and does not count. It is ``None`` when that probe
    could not be measured, again rather than a fabricated zero.
    """

    status: LlmRuntimeStatus
    detail: str
    gpu_usage_percent: int | None
    active_model_count: int | None
    available_model_names: tuple[str, ...]
    running_model_names: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class LlmServer:
    """Screen 09's server card: the runtime snapshot plus the shared box's name.

    This reports read-only connection and loaded-model status only. It does
    not promise that a project's documents, mail and meetings are processed by
    an isolated model; that is a project-model assignment concern, not this
    module's to guarantee.
    """

    name: str
    network_note: str
    status: LlmRuntimeStatus
    detail: str
    gpu_usage_percent: int | None
    active_model_count: int | None
    available_model_names: tuple[str, ...]
    running_model_names: tuple[str, ...]
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


@dataclass(frozen=True, slots=True)
class ProjectRepositoryConnection:
    """One GitHub repository connection per project."""

    id: str
    project_id: str
    provider: str
    repository: str
    version: int
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class ProjectRepositoryConnectionAudit:
    """Change audit trail for repository connections."""

    id: str
    connection_id: str
    project_id: str
    actor_id: str
    previous_repository: str | None
    new_repository: str
    created_at: datetime
