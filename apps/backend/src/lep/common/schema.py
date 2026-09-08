"""Table registry and schema creation.

Every module declares its own tables against the shared ``Base``. SQLAlchemy only
knows about a table once its module has been imported, so this file imports them
all in one place. Alembic and the startup check both go through here, which means
a module whose tables are missing from this list simply has no schema — a failure
that shows up immediately rather than as a confusing runtime error.
"""

from __future__ import annotations

import logging

from sqlalchemy import inspect

from .db import Base, engine

logger = logging.getLogger("lep.schema")


def load_all_models() -> None:
    """Import every module's tables so the shared metadata is complete."""

    # noqa comments: imported for the side effect of registering mappers.
    from ..modules.delivery.infrastructure import models as delivery_models  # noqa: F401
    from ..modules.iam.infrastructure import models as iam_models  # noqa: F401
    from ..modules.projects.infrastructure import models as project_models  # noqa: F401


def create_all() -> None:
    """Create any missing table.

    Alembic owns schema *changes*; this creates the initial schema on a fresh
    database so a first deployment does not need a separate migration step. It
    never drops or alters anything, so running it against an existing database
    is a no-op.
    """

    load_all_models()
    Base.metadata.create_all(bind=engine())
    names = sorted(inspect(engine()).get_table_names())
    logger.info("schema_ready", extra={"tables": names})


def table_names() -> list[str]:
    load_all_models()
    return sorted(Base.metadata.tables)
