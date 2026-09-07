"""Stable public interface for the integrations module."""

from __future__ import annotations

from functools import lru_cache

from ...common.adapters import vcs_choice
from .application.services import IntegrationPort, IntegrationService
from .infrastructure.fixtures import FixtureIntegrationAdapter
from .infrastructure.github_vcs import GitHubIntegrationAdapter, GitHubVcsAdapter

__all__ = ["get_integration_service"]


def _adapter() -> IntegrationPort:
    """Pick the repository adapter per ADR-018. Default is the fixture.

    Only the repository half goes real today. The local LLM half keeps its
    fixture until WP-PKD-033, and screen 09 says so rather than implying a
    server exists.
    """

    fixture = FixtureIntegrationAdapter()
    if not vcs_choice().use_real:
        return fixture
    return GitHubIntegrationAdapter(github=GitHubVcsAdapter.from_env(), fallback=fixture)


@lru_cache(maxsize=1)
def get_integration_service() -> IntegrationService:
    return IntegrationService(_adapter())
