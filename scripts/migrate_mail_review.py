"""Create the mail review tables (ADR-021, WP-PKD-MAIL-APPROVAL-20260909).

Additive only: creates ``mail_reviews``, ``mail_review_attachments``,
``mail_idempotency_keys``, ``mail_idempotency_links``, ``mail_audit_log``, and
``document_mail_attachment_links`` (the documents-owned mail link table that
this same work package introduced) if they are missing. Never touches an
existing table, never drops anything, and never prints the database DSN
(only the table names it found or created).

Dry-run by default — it reports what it *would* create. Pass ``--apply`` to
actually create the missing tables. Safe to run more than once: creating an
already-existing table is a no-op.

Usage::

    uv run python scripts/migrate_mail_review.py            # dry run
    uv run python scripts/migrate_mail_review.py --apply     # create tables
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_BACKEND_SRC = Path(__file__).resolve().parent.parent / "apps" / "backend" / "src"
if str(_BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(_BACKEND_SRC))

#: Tables this script owns. Anything else in ``Base.metadata`` is left alone —
#: this migration touches mail-owned schema only.
_OWNED_TABLES = frozenset(
    {
        "mail_reviews",
        "mail_review_attachments",
        "mail_idempotency_keys",
        "mail_idempotency_links",
        "mail_audit_log",
        "document_mail_attachment_links",
    }
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply", action="store_true", help="Actually create missing tables (default: dry run)."
    )
    args = parser.parse_args(argv)

    from sqlalchemy import inspect
    from sqlalchemy.exc import SQLAlchemyError

    from lep.common.db import Base, engine
    from lep.common.schema import load_all_models

    try:
        load_all_models()
        bound = engine()
        existing = set(inspect(bound).get_table_names())
    except (RuntimeError, SQLAlchemyError, OSError):
        # Never print the driver's own exception text or a traceback here:
        # for a bad or unreachable DSN, that text routinely echoes the
        # connection string itself — host, user, sometimes the password.
        # Report only that something is wrong, never what.
        print("database is not reachable or misconfigured; check LEP_DATABASE_URL.")
        return 1

    # A table this script expects but that never registered against
    # ``Base.metadata`` means a model failed to import or was renamed — that
    # is a bug worth failing loudly on, not a table to quietly skip.
    unregistered = sorted(_OWNED_TABLES - set(Base.metadata.tables))
    if unregistered:
        raise RuntimeError(
            "expected mail-owned table(s) not registered in schema metadata: "
            f"{', '.join(unregistered)}"
        )

    owned_tables = [Base.metadata.tables[name] for name in sorted(_OWNED_TABLES)]
    missing = sorted(t.name for t in owned_tables if t.name not in existing)

    if not missing:
        print("mail review tables already present; nothing to do.")
        return 0

    if not args.apply:
        print("dry run — would create:")
        for name in missing:
            print(f"  {name}")
        print("re-run with --apply to create them.")
        return 0

    Base.metadata.create_all(bind=bound, tables=owned_tables)
    print("created:")
    for name in missing:
        print(f"  {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
