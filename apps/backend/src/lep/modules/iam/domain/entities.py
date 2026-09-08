"""Identity domain: users and sessions.

No framework imports here. ``scripts/check_boundaries.py`` enforces that, which
is what lets the SQLAlchemy mapping live entirely in the infrastructure layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class UserRole(StrEnum):
    """첫 가입자가 관리자가 되고 이후 가입자는 일반 사용자다."""

    ADMIN = "admin"
    MEMBER = "member"


class UserStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"


@dataclass(frozen=True, slots=True)
class User:
    id: str
    email: str
    display_name: str
    role: UserRole
    status: UserStatus
    created_at: datetime

    @property
    def is_admin(self) -> bool:
        return self.role is UserRole.ADMIN

    @property
    def initial(self) -> str:
        """상단바 아바타에 쓰는 한 글자."""

        return self.display_name[:1] if self.display_name else self.email[:1].upper()


@dataclass(frozen=True, slots=True)
class Session:
    id: str
    user_id: str
    created_at: datetime
    expires_at: datetime
    #: 마지막으로 이 세션이 쓰인 시각. 세션 목록 화면에서 쓴다.
    last_seen_at: datetime

    def is_expired(self, now: datetime) -> bool:
        return now >= self.expires_at
