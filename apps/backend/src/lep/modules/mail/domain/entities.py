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
class MailAttachment:
    """메일에 딸려 온 파일 하나.

    내용은 담지 않는다. 3.6MB짜리 zip이 오가는 메일함이라 목록을 만들 때마다
    본문에 실어 나르면 화면이 그 무게를 그대로 진다. 내려받을 때 다시 읽는다.
    """

    #: 사람이 읽는 이름. RFC 2047로 인코딩돼 오므로 디코딩한 값이다.
    filename: str
    content_type: str
    size_bytes: int
    #: 메일 안에서 몇 번째 부분인지. 내려받을 때 이걸로 찾는다.
    part_index: int
    #: 승인 시 documents 드라이브에 연결된 참조 ID. 승인 전이거나 선택되지
    #: 않았으면 ``None``이다 (ADR-021).
    linked_file_id: str | None = None


@dataclass(frozen=True, slots=True)
class MailProjectSuggestion:
    """Recommendation for a project, with confidence and reasons."""

    project_id: str
    project_name: str
    confidence: Confidence
    reasons: tuple[str, ...]


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
    #: 딸려 온 파일들. "자료 전달의 건"에서는 이쪽이 본론이다.
    attachments: tuple[MailAttachment, ...] = ()
    #: 발신 도메인 등에서 나온 추천. 확정이 아니다 (ADR-021).
    suggested_project_id: str | None = None
    #: 프로젝트 맥락 기반 추천. 최대 3개까지, 미분류 메일에만 계산 (Task 4).
    suggestions: tuple[MailProjectSuggestion, ...] = ()
    #: 낙관적 잠금에 쓰는 버전. 승인 전에는 항상 0이다.
    version: int = 0
    #: 사람이 승인했을 때만 채워진다. overlay만으로는 채울 수 없다.
    approved_by: str | None = None
    approved_at: datetime | None = None
