"""Identity HTTP routes: signup, login, logout, whoami."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session as DbSession

from ....common.db import get_session
from ....common.envelope import Envelope, single
from ..application.services import SESSION_LIFETIME, IdentityService, LoginResult
from ..domain.entities import User
from ..public import SESSION_COOKIE, CurrentUser, cookie_secure

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class UserOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    email: str
    display_name: str
    role: str
    initial: str

    @classmethod
    def of(cls, user: User) -> UserOut:
        return cls(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            role=user.role.value,
            initial=user.initial,
        )


class SignupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=5, max_length=320)
    display_name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=200)


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=1, max_length=320)
    password: str = Field(min_length=1, max_length=200)


class SignupStateOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    #: 아직 아무도 가입하지 않았으면 다음 가입자가 관리자가 된다.
    first_account: bool


class SessionOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    created_at: datetime
    last_seen_at: datetime
    expires_at: datetime


def _set_cookie(response: Response, result: LoginResult) -> None:
    """세션 쿠키를 심는다.

    httponly라 자바스크립트가 읽지 못하고, lax라 다른 사이트에서 넘어온 POST에는
    실리지 않는다. secure는 TLS 뒤에 있을 때만 켠다. HTTP에서 켜면 브라우저가
    쿠키를 저장하지 않아 로그인 자체가 되지 않는다.
    """

    response.set_cookie(
        key=SESSION_COOKIE,
        value=result.token,
        max_age=int(SESSION_LIFETIME.total_seconds()),
        httponly=True,
        samesite="lax",
        secure=cookie_secure(),
        path="/",
    )


@router.get("/signup-state", response_model=Envelope[SignupStateOut])
def signup_state(
    db: Annotated[DbSession, Depends(get_session)],
) -> Envelope[SignupStateOut]:
    """가입 화면이 "첫 계정은 관리자가 됩니다"를 보여줄지 판단하는 데 쓴다."""

    return single(SignupStateOut(first_account=IdentityService(db).user_count() == 0))


@router.post("/signup", response_model=Envelope[UserOut], status_code=201)
def signup(
    request: SignupRequest,
    response: Response,
    db: Annotated[DbSession, Depends(get_session)],
) -> Envelope[UserOut]:
    result = IdentityService(db).signup(
        email=request.email,
        display_name=request.display_name,
        password=request.password,
    )
    _set_cookie(response, result)
    return single(UserOut.of(result.user))


@router.post("/login", response_model=Envelope[UserOut])
def login(
    request: LoginRequest,
    response: Response,
    db: Annotated[DbSession, Depends(get_session)],
) -> Envelope[UserOut]:
    result = IdentityService(db).login(email=request.email, password=request.password)
    _set_cookie(response, result)
    return single(UserOut.of(result.user))


# 204는 본문을 가질 수 없으므로 응답 모델을 명시적으로 끈다.
@router.post("/logout", status_code=204, response_model=None)
def logout(
    response: Response,
    db: Annotated[DbSession, Depends(get_session)],
    lep_session: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> None:
    # 쿠키는 어떤 경우에도 지운다. 세션이 이미 만료됐어도 브라우저에 남은 값을
    # 그대로 두면 다음 요청에서 또 실패한다.
    if lep_session:
        IdentityService(db).logout(lep_session)
    response.delete_cookie(SESSION_COOKIE, path="/")


@router.get("/me", response_model=Envelope[UserOut])
def me(user: CurrentUser) -> Envelope[UserOut]:
    return single(UserOut.of(user))


@router.get("/sessions", response_model=Envelope[list[SessionOut]])
def sessions(
    user: CurrentUser,
    db: Annotated[DbSession, Depends(get_session)],
) -> Envelope[list[SessionOut]]:
    items = IdentityService(db).list_sessions(user.id)
    return single(
        [
            SessionOut(
                id=s.id,
                created_at=s.created_at,
                last_seen_at=s.last_seen_at,
                expires_at=s.expires_at,
            )
            for s in items
        ]
    )
