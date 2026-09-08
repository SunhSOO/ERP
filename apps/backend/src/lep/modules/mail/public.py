"""Stable public interface for the mail module."""

from __future__ import annotations

from functools import lru_cache

from ...common.adapters import mail_choice
from .application.services import MailPort, MailService
from .infrastructure.fixtures import EmptyMailAdapter
from .infrastructure.hiworks_pop3 import HiworksMailAdapter

__all__ = ["get_mail_service", "unclassified_count"]


def _adapter() -> MailPort:
    """ADR-018에 따라 어댑터를 고른다. 기본은 빈 어댑터다."""

    return HiworksMailAdapter.from_env() if mail_choice().use_real else EmptyMailAdapter()


@lru_cache(maxsize=1)
def get_mail_service() -> MailService:
    return MailService(_adapter())


def unclassified_count(project_id: str) -> int:
    """홈 카드가 쓰는 미분류 건수. 메일 연동이 없으면 0이다."""

    return get_mail_service().unclassified_count(project_id)
