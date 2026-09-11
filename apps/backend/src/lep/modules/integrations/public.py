"""Stable public interface for the integrations module."""

from __future__ import annotations

from functools import lru_cache

from ...common.adapters import llm_base_url, llm_choice, vcs_choice
from .application.services import IntegrationPort, IntegrationService
from .domain.ports import LlmRuntimePort
from .infrastructure.fixtures import FixtureIntegrationAdapter
from .infrastructure.github_vcs import GitHubIntegrationAdapter, GitHubVcsAdapter
from .infrastructure.llm_runtime import FixtureLlmRuntimeAdapter, OllamaLlmRuntimeAdapter

__all__ = ["get_integration_service"]


def _adapter() -> IntegrationPort:
    """Pick the repository adapter per ADR-018. Default is the fixture.

    Only the repository half goes real today. The project-model list (name,
    priority, GPU share) stays on the fixture until settings persistence
    exists; only the LLM *runtime status* (below) is live.
    """

    fixture = FixtureIntegrationAdapter()
    if not vcs_choice().use_real:
        return fixture
    return GitHubIntegrationAdapter(github=GitHubVcsAdapter.from_env(), fallback=fixture)


def _llm_runtime_adapter() -> LlmRuntimePort:
    """Pick the LLM runtime adapter per ADR-018 (WP-PKD-033A).

    Deliberately independent of ``_adapter()``/``vcs_choice()`` above: the
    runtime snapshot reflects ``LEP_ADAPTER_LLM`` alone, not which VCS adapter
    happens to be selected.
    """

    choice = llm_choice()
    if not choice.use_real:
        return FixtureLlmRuntimeAdapter(unavailable_reason=choice.unavailable_reason)
    return OllamaLlmRuntimeAdapter(base_url=llm_base_url())


@lru_cache(maxsize=1)
def get_integration_service() -> IntegrationService:
    return IntegrationService(_adapter(), _llm_runtime_adapter())
