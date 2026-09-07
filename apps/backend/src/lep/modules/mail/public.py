"""Stable public interface for the mail module.

Projects (the home screen) needs the unclassified count for its cards. It reads it
through here rather than from mail's storage.
"""

from __future__ import annotations

from functools import lru_cache

from ...common.adapters import mail_choice
from .application.services import MailPort, MailService
from .infrastructure.fixtures import FixtureMailAdapter
from .infrastructure.hiworks_imap import HiworksMailAdapter

__all__ = ["get_mail_service", "unclassified_count"]


def _adapter() -> MailPort:
    """Pick the mail adapter per ADR-018. Default is the fixture."""

    return HiworksMailAdapter.from_env() if mail_choice().use_real else FixtureMailAdapter()


@lru_cache(maxsize=1)
def get_mail_service() -> MailService:
    return MailService(_adapter())


def unclassified_count(project_id: str) -> int:
    return get_mail_service().unclassified_count(project_id)
