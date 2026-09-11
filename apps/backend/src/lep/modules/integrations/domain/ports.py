"""Read-only LLM runtime port (WP-PKD-033A, ADR-018).

Kept separate from ``IntegrationPort`` in ``application/services.py``, which
still owns the VCS fixture/real composite and the (unpersisted) project-model
list. This port only reads the status of whichever inference server is
currently configured. It never performs inference, model pull, load/unload or
restart; there is no method here that could.
"""

from __future__ import annotations

from typing import Protocol

from .entities import LlmRuntimeSnapshot


class LlmRuntimePort(Protocol):
    def snapshot(self) -> LlmRuntimeSnapshot:
        """A best-effort, short-timeout read of the server's current status."""
        ...
