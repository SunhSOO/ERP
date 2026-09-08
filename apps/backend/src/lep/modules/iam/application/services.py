"""Identity use cases: signup, login, logout, session lookup.

Signup policy: the first account to register becomes the administrator and every
account after that is an ordinary member. That is a deliberate, stated rule
rather than an accident of ordering, so it is enforced inside a transaction — two
simultaneous first signups cannot both become admin.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DbSession

from ....common.db import as_utc
from ....common.problems import ProblemError
from ..domain.entities import Session, User, UserRole, UserStatus
from ..infrastructure.models import SessionRow, UserRow

#: 세션 수명. 사내 도구이므로 넉넉하게 두되 무한은 아니다.
SESSION_LIFETIME = timedelta(days=14)

MIN_PASSWORD_LENGTH = 10

_hasher = PasswordHasher()


def hash_token(token: str) -> str:
    """세션 토큰의 저장용 해시.

    토큰은 이미 고엔트로피 난수라 느린 해시가 필요 없다. 목적은 데이터베이스가
    새더라도 토큰 원문을 얻지 못하게 하는 것뿐이다.
    """

    return hashlib.sha256(token.encode()).hexdigest()


def normalise_email(email: str) -> str:
    return email.strip().lower()


@dataclass(frozen=True, slots=True)
class LoginResult:
    user: User
    token: str
    expires_at: datetime


def _to_user(row: UserRow) -> User:
    return User(
        id=row.id,
        email=row.email,
        display_name=row.display_name,
        role=UserRole(row.role),
        status=UserStatus(row.status),
        created_at=as_utc(row.created_at),
    )


class IdentityService:
    def __init__(self, db: DbSession) -> None:
        self._db = db

    # ── 가입 ───────────────────────────────────────────────────────────────
    def signup(self, *, email: str, display_name: str, password: str) -> LoginResult:
        address = normalise_email(email)
        name = display_name.strip()

        if "@" not in address or len(address) < 5:
            raise ProblemError("VALIDATION_FAILED", "이메일 형식이 올바르지 않습니다.")
        if not name:
            raise ProblemError("VALIDATION_FAILED", "이름을 입력해 주세요.")
        if len(password) < MIN_PASSWORD_LENGTH:
            raise ProblemError(
                "VALIDATION_FAILED",
                f"비밀번호는 {MIN_PASSWORD_LENGTH}자 이상이어야 합니다.",
            )

        # 첫 계정이 관리자가 된다. 같은 트랜잭션에서 세므로 두 명이 동시에
        # 가입해도 둘 다 관리자가 되지는 않는다.
        existing = self._db.scalar(select(func.count()).select_from(UserRow)) or 0
        role = UserRole.ADMIN if existing == 0 else UserRole.MEMBER

        row = UserRow(
            id=str(uuid.uuid4()),
            email=address,
            display_name=name,
            password_hash=_hasher.hash(password),
            role=role.value,
            status=UserStatus.ACTIVE.value,
        )
        self._db.add(row)
        try:
            self._db.flush()
        except IntegrityError as exc:
            self._db.rollback()
            raise ProblemError("STATE_CONFLICT", "이미 가입된 이메일입니다.") from exc

        return self._issue_session(row)

    # ── 로그인 ─────────────────────────────────────────────────────────────
    def login(self, *, email: str, password: str) -> LoginResult:
        row = self._db.scalar(
            select(UserRow).where(UserRow.email == normalise_email(email))
        )

        # 계정이 없을 때도 해시를 한 번 돌려 응답 시간으로 가입 여부가 새지
        # 않게 한다. 오류 문구도 두 경우를 구분하지 않는다.
        if row is None:
            _hasher.hash(password)
            raise ProblemError("VALIDATION_FAILED", "이메일 또는 비밀번호가 올바르지 않습니다.")

        try:
            _hasher.verify(row.password_hash, password)
        except (VerifyMismatchError, VerificationError) as exc:
            raise ProblemError(
                "VALIDATION_FAILED", "이메일 또는 비밀번호가 올바르지 않습니다."
            ) from exc

        if row.status != UserStatus.ACTIVE.value:
            # 정지 사유를 밖으로 알리지 않는다.
            raise ProblemError(
                "VALIDATION_FAILED", "로그인할 수 없는 계정입니다. 관리자에게 문의하세요."
            )

        # argon2 파라미터가 바뀌었으면 이 기회에 다시 해시한다.
        if _hasher.check_needs_rehash(row.password_hash):
            row.password_hash = _hasher.hash(password)

        return self._issue_session(row)

    def _issue_session(self, row: UserRow) -> LoginResult:
        token = secrets.token_urlsafe(32)
        now = datetime.now(tz=UTC)
        expires = now + SESSION_LIFETIME
        self._db.add(
            SessionRow(
                id=str(uuid.uuid4()),
                user_id=row.id,
                token_hash=hash_token(token),
                created_at=now,
                expires_at=expires,
                last_seen_at=now,
            )
        )
        self._db.flush()
        return LoginResult(user=_to_user(row), token=token, expires_at=expires)

    # ── 세션 ───────────────────────────────────────────────────────────────
    def resolve(self, token: str) -> User | None:
        """토큰으로 사용자를 찾는다. 만료됐으면 정리하고 ``None``을 낸다."""

        if not token:
            return None

        row = self._db.scalar(
            select(SessionRow).where(SessionRow.token_hash == hash_token(token))
        )
        if row is None:
            return None

        now = datetime.now(tz=UTC)
        if now >= as_utc(row.expires_at):
            self._db.delete(row)
            return None

        # 마지막 사용 시각은 분 단위로만 갱신한다. 매 요청 쓰기를 하지 않는다.
        if (now - as_utc(row.last_seen_at)) > timedelta(minutes=5):
            row.last_seen_at = now

        user_row = self._db.get(UserRow, row.user_id)
        if user_row is None or user_row.status != UserStatus.ACTIVE.value:
            return None
        return _to_user(user_row)

    def logout(self, token: str) -> None:
        row = self._db.scalar(
            select(SessionRow).where(SessionRow.token_hash == hash_token(token))
        )
        if row is not None:
            self._db.delete(row)

    def list_sessions(self, user_id: str) -> list[Session]:
        rows = self._db.scalars(
            select(SessionRow)
            .where(SessionRow.user_id == user_id)
            .order_by(SessionRow.last_seen_at.desc())
        ).all()
        return [
            Session(
                id=r.id,
                user_id=r.user_id,
                created_at=as_utc(r.created_at),
                expires_at=as_utc(r.expires_at),
                last_seen_at=as_utc(r.last_seen_at),
            )
            for r in rows
        ]

    def user_count(self) -> int:
        return self._db.scalar(select(func.count()).select_from(UserRow)) or 0
