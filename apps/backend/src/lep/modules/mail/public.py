"""Stable public interface for the mail module."""

from __future__ import annotations

from functools import lru_cache

from sqlalchemy.orm import Session as DbSession

from ...common.adapters import mail_choice
from ..iam.public import User
from .domain.ports import MailPort
from .infrastructure.fixtures import EmptyMailAdapter
from .infrastructure.hiworks_pop3 import HiworksMailAdapter

__all__ = ["get_mail_service", "unclassified_count"]


def _adapter() -> MailPort:
    """ADR-018에 따라 어댑터를 고른다. 기본은 빈 어댑터다."""

    return HiworksMailAdapter.from_env() if mail_choice().use_real else EmptyMailAdapter()


@lru_cache(maxsize=1)
def get_mail_service() -> MailPort:
    """현재 선택된 메일 어댑터.

    이름은 예전 ``MailService`` 시절 그대로 남긴다 — ``conftest.py``가
    ``get_mail_service.cache_clear()``로 테스트마다 이 캐시를 비운다.
    """

    return _adapter()


def unclassified_count(db: DbSession, project_id: str, actor: User) -> int:
    """홈 카드가 쓰는 미분류 건수.

    미분류 공용 검토함은 관리자만 볼 수 있으므로(ADR-021), 관리자가 아닌
    호출자에게는 항상 0을 돌려준다.
    """

    from .application.services import MailReviewService

    return MailReviewService(db, get_mail_service(), actor).counts(project_id)["unclassified"]
