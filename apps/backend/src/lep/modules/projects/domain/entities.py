"""Project domain entities.

The domain layer holds no framework imports. ``scripts/check_boundaries.py``
enforces that, which is what keeps the SQLAlchemy mapping in infrastructure.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

#: 프로젝트 코드는 볼트 폴더 이름이 되고 업로드 경로에도 들어간다. 경로 조작과
#: 파일 시스템 사고를 막기 위해 문자 집합을 좁게 잡는다.
CODE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{1,39}$")


class ViewRole(StrEnum):
    """계약에서 우리가 어느 쪽인지."""

    VENDOR = "vendor"
    CLIENT = "client"


class SyncHealth(StrEnum):
    """연동 상태. 색상만으로 표현하지 않고 항상 글리프와 문구가 함께 간다."""

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
    created_by: str
    created_at: datetime
    archived: bool = False


@dataclass(frozen=True, slots=True)
class ProjectSummary:
    """홈 화면 카드.

    갓 만든 프로젝트는 아직 아무 데이터도 없다. 그 상태를 0이나 빈 값으로
    보여주는 것이 정상이며, 없는 진행률을 만들어 내지 않는다.
    """

    project_id: str
    wbs_progress_percent: int | None
    schedule_note: str | None
    vault_health: SyncHealth
    vault_note: str
    unclassified_mail_count: int
    vcs_health: SyncHealth
    vcs_note: str
    task_count: int = 0
    statement_count: int = 0
