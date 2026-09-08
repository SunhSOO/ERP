"""Mail domain: messages and their project classification."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class Confidence(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Classification(StrEnum):
    #: Assigned to a project.
    PROJECT = "project"
    #: Looks project-related but the classifier is not sure yet.
    UNCLASSIFIED = "unclassified"
    #: Explicitly not about any project.
    UNRELATED = "unrelated"


class MailAction(StrEnum):
    """The three buttons on screen 06."""

    PROMOTE_TO_NOTE = "promote_to_note"
    APPLY_TO_WBS = "apply_to_wbs"
    DISMISS = "dismiss"


@dataclass(frozen=True, slots=True)
class MailMessage:
    id: str
    sender_name: str
    sender_org: str
    received_at: datetime
    subject: str
    body: str
    classification: Classification
    project_id: str | None
    #: What the classifier thinks the message is about, e.g. 일정 변경.
    intent: str | None
    confidence: Confidence | None
    #: Which milestone the message concerns, by code.
    milestone_code: str | None = None
    note_id: str | None = None
    handled: bool = False
