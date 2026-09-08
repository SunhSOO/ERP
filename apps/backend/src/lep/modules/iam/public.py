"""Stable public interface for the identity module.

Every other module asks "who is calling?" through here. Nothing reaches into
identity's tables.
"""

from __future__ import annotations

import os
from typing import Annotated

from fastapi import Cookie, Depends
from sqlalchemy.orm import Session as DbSession

from ...common.db import get_session
from ...common.problems import ProblemError
from .application.services import IdentityService
from .domain.entities import User

__all__ = [
    "SESSION_COOKIE",
    "CurrentUser",
    "User",
    "cookie_secure",
    "current_user",
    "optional_user",
]

SESSION_COOKIE = "lep_session"


def cookie_secure() -> bool:
    """HTTPS 뒤에 있을 때만 Secure를 켠다.

    사내망 HTTP로 띄운 상태에서 Secure를 켜면 브라우저가 쿠키를 저장하지 않아
    로그인 자체가 되지 않는다. 역방향 프록시와 TLS가 생기면 이 값을 1로 둔다.
    """

    return os.getenv("LEP_COOKIE_SECURE", "0").strip() == "1"


def optional_user(
    db: Annotated[DbSession, Depends(get_session)],
    lep_session: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> User | None:
    """세션이 있으면 사용자를, 없으면 ``None``을 낸다."""

    if not lep_session:
        return None
    return IdentityService(db).resolve(lep_session)


def current_user(
    user: Annotated[User | None, Depends(optional_user)],
) -> User:
    """인증을 요구하는 엔드포인트의 의존성.

    권한이 없을 때 화면이 필요한 권한과 문의 대상을 말할 수 있도록 Problem
    Details로 떨어뜨린다.
    """

    if user is None:
        raise ProblemError("AUTHENTICATION_REQUIRED", "로그인이 필요합니다.")
    return user


CurrentUser = Annotated[User, Depends(current_user)]
