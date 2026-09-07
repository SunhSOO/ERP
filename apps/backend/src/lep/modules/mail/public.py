"""Stable public interface for the mail module.

Projects (the home screen) needs the unclassified count for its cards. It reads it
through here rather than from mail's storage.
"""

from __future__ import annotations

from functools import lru_cache

from .application.services import MailService
from .infrastructure.fixtures import FixtureMailAdapter

__all__ = ["get_mail_service", "unclassified_count"]


@lru_cache(maxsize=1)
def get_mail_service() -> MailService:
    return MailService(FixtureMailAdapter())


def unclassified_count(project_id: str) -> int:
    return get_mail_service().unclassified_count(project_id)
