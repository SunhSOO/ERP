# Backend module boundaries

Each domain module follows this shape:

```text
modules/<domain>/
├── public.py
├── api/
├── application/
├── domain/
├── infrastructure/
├── events/
├── permissions/
└── tests/
```

`public.py` is the only stable import surface exposed to another module.
Internal `domain`, `application`, `infrastructure`, `api`, `events`, and
`permissions` modules are private to their owner. The architecture checker
rejects cross-module internal imports and rejects FastAPI, SQLAlchemy, Redis,
and MinIO imports from the domain layer.

One module owns each table. Other modules must use an application interface or
an event; they must not write another module's tables directly. WP-PLT-001
creates only the `core` module skeleton and no business tables.

Run the check from the repository root:

```text
python scripts/check_boundaries.py
```
