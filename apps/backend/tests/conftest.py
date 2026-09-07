"""Shared test fixtures.

The in-memory adapters keep their data in module-level containers, and the write
endpoints mutate it on purpose so the screens are genuinely interactive. That
makes tests order-dependent unless the state is restored between them.

Rather than adding a bespoke ``reset()`` to every adapter, this snapshots the
mutable module-level containers and restores them around each test. When
WP-PKD-020 swaps in PostgreSQL, this fixture becomes a transaction rollback and
the tests themselves do not change.

Every import of application code is deferred into a fixture body. Importing the
FastAPI app at conftest scope would configure logging before pytest has finished
installing its output capture, and the resulting handler outlives the stream it
was given.
"""

from __future__ import annotations

from collections.abc import Iterator
from importlib import import_module
from types import ModuleType
from typing import Any

import pytest

FIXTURE_MODULES = (
    "lep.modules.projects.infrastructure.memory",
    "lep.modules.delivery.infrastructure.memory",
    "lep.modules.knowledge.infrastructure.fixture_vault",
    "lep.modules.documents.infrastructure.fixtures",
    "lep.modules.mail.infrastructure.fixtures",
    "lep.modules.integrations.infrastructure.fixtures",
)


def _mutable_containers(module: ModuleType) -> list[list[Any] | dict[Any, Any]]:
    # Dunder names must be excluded, not just skipped for tidiness: ``vars()``
    # includes ``__builtins__``, which is a dict. Clearing that one detonates the
    # interpreter rather than failing a test.
    return [
        value
        for name, value in vars(module).items()
        if name.startswith("_")
        and not name.startswith("__")
        and isinstance(value, list | dict)
    ]


@pytest.fixture
def client() -> Iterator[Any]:
    """A TestClient over a fresh app, with fixture data restored afterwards.

    Entities are frozen dataclasses, so a shallow copy of each container is a
    complete snapshot.
    """

    from fastapi.testclient import TestClient

    from lep.bootstrap.app import create_app

    snapshots: list[tuple[list[Any] | dict[Any, Any], list[Any] | dict[Any, Any]]] = []
    for path in FIXTURE_MODULES:
        for container in _mutable_containers(import_module(path)):
            snapshots.append((container, container.copy()))

    # Deliberately not used as a context manager. Entering it runs the app's
    # lifespan on a portal thread, which does not shut down cleanly here and
    # takes the interpreter down with it. Nothing in this track uses lifespan.
    yield TestClient(create_app())

    for container, snapshot in snapshots:
        container.clear()
        if isinstance(container, list):
            container.extend(snapshot)
        else:
            container.update(snapshot)
