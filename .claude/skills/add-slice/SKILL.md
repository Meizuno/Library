---
name: add-slice
description: Generate a new module (bounded-context slice) with the project's flat-per-module layout (models / ports / exceptions / repositories / use_cases / api).
---

# Add Module (Bounded-Context Slice)

When the human says "add a new module X" or "add slice X" (e.g., "add `reservation/`", "add `payment/`"), follow this skill to create the **complete flat-file skeleton**.

This is a **bigger** task than `/add-use-case`. Only use it when introducing a **new aggregate root** with its own lifecycle, not a new operation on an existing one.

## Pre-flight

1. Read [AGENTS.md](../../../AGENTS.md) — confirm flat-layout rules and cross-module import policy.
2. Read existing modules as reference:
   - [`book/`](../../../library/book/) — simplest standalone module (no cross-module deps, full CRUD, VO + cache decorator)
   - [`member/`](../../../library/member/) — has VOs (Email, Password), credential + JWT adapters co-located in `repositories.py`
   - [`loan/`](../../../library/loan/) — multi-aggregate (consumes Book and Member ports), no cache, no VOs
   - [`auth/`](../../../library/auth/) — defines ports consumed by other modules, has its own `api/security.py`
   - [`notification/`](../../../library/notification/) — minimal (port + impl, no use cases, no api)

## Workflow

### Step 1 — Confirm scope with the human

Before generating the skeleton, ask:

- What's the **aggregate root** for this module? (entity name)
- What **VOs** does it own? (e.g., Reservation owns `ReservationCode`, `ReservationStatus`)
- What **use cases** are needed initially? List them as `<verb>_<noun>`.
- Does it **consume ports** from other modules? Which?
- Does it **expose ports** for other modules to consume?
- Will it have a **REST API**, or is it driven by other modules only (like `notification/`)?
- Cache decorator? (Books and Members have it; Loans and Auth do not.)
- Soft delete on this aggregate? (Books and Members do; Loans and RefreshTokens do not.) See `deleted_at` pattern in [`books_table`](../../../library/book/repositories.py) / [`members_table`](../../../library/member/repositories.py).

**Wait for human confirmation. Do not generate the skeleton without it.**

### Step 2 — Generate the flat module skeleton

```
library/<module>/
├── __init__.py
├── models.py            # Entity + any VOs (framework-free)
├── ports.py             # All Protocols owned by this module (framework-free)
├── exceptions.py        # DomainError + ApplicationError subclasses
├── repositories.py      # <entity>_table + Sql impl (+ Cached if caching is decided)
│                        #   + any non-repo adapters this module provides for other modules' ports
├── use_cases/
│   ├── __init__.py
│   └── <each use case>.py   # Command DTO + UseCase class together
└── api/                 # only if the module is exposed via HTTP
    ├── __init__.py      # aggregator: APIRouter() + include_router(...) per route
    ├── dependencies.py  # feature-local DI providers
    ├── schemas.py       # shared response shape (e.g., <Entity>Response)
    └── routes/
        ├── __init__.py
        └── <each route>.py  # APIRouter(prefix=...) + request schema + handler
```

Minimal-module shape (no api / no use_cases — only `notification/` looks like this):

```
library/<module>/
├── __init__.py
├── models.py
├── ports.py
└── <impl>.py            # e.g., email_notifier.py
```

Also create the **test tree** mirroring source:

```
tests/<module>/
├── __init__.py
├── test_models.py       # entity + VO tests
├── repositories/
│   ├── __init__.py
│   ├── conftest.py      # parametrized empty_<entity>_repo fixture (sql, optionally cache_*)
│   ├── test_contract.py # protocol-satisfaction + behavior contract
│   ├── test_cached.py   # only if a Cached*Repository exists
│   └── test_soft_delete.py  # only if soft-delete is part of the spec
├── use_cases/
│   ├── __init__.py
│   ├── conftest.py      # local fixtures (e.g., a default command)
│   └── test_<each use case>.py
└── api/
    ├── __init__.py
    └── test_api.py      # end-to-end HTTP behavior
```

### Step 3 — Generate the entity (models.py)

Mirror [`Book`](../../../library/book/models.py) or [`Member`](../../../library/member/models.py):

```python
from dataclasses import dataclass, field
from uuid import UUID, uuid4


@dataclass(kw_only=True)
class <Entity>:
    id: UUID = field(init=False, default_factory=uuid4)
    # ... fields ...

    def __post_init__(self) -> None:
        # validation only — no I/O
        ...

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, <Entity>):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    # state transitions as methods (e.g., mark_verified, cancel)
```

### Step 4 — Generate VOs (in the same models.py)

Mirror [`ISBN`](../../../library/book/models.py) or [`Email`](../../../library/member/models.py):

```python
@dataclass(frozen=True)
class <ValueObject>:
    value: str

    def __post_init__(self) -> None:
        # validation; normalization via object.__setattr__ (frozen workaround)
        ...
```

VOs go in the **same `models.py`** as the entity unless the file is genuinely getting unwieldy — keep the module flat.

### Step 5 — Generate the ports (ports.py)

Mirror [`BookRepository`](../../../library/book/ports.py):

```python
from typing import Protocol, runtime_checkable
from uuid import UUID

from library.<module>.models import <Entity>


@runtime_checkable
class <Entity>Repository(Protocol):
    async def find_by_id(self, id: UUID) -> <Entity> | None: ...
    async def create(self, entity: <Entity>) -> None: ...
    async def update(self, entity: <Entity>) -> None: ...
    async def delete(self, id: UUID) -> None: ...
    async def list_all(self) -> list[<Entity>]: ...
```

- `@runtime_checkable` lets the `test_satisfies_<port>_protocol` test use `isinstance(impl, Port)`.
- **`create` and `update` are separate** — no upserts.
- Add domain-specific queries (`find_by_email`, `find_active_due_on`) as needed.
- Any service ports the module owns go in this same file.

### Step 6 — Generate exceptions (exceptions.py)

```python
from library.shared.exceptions import ApplicationError, DomainError


class <Entity>NotFound(DomainError):
    pass


class <Entity>AlreadyExists(ApplicationError):
    pass


# ... other domain / application exceptions for this module ...
```

Domain exceptions extend `DomainError`; application exceptions extend `ApplicationError`. Both bases live in [`library/shared/exceptions.py`](../../../library/shared/exceptions.py).

### Step 7 — Generate the SQL table + repository (repositories.py)

Mirror [`SqlBookRepository`](../../../library/book/repositories.py):

```python
from typing import Any
from uuid import UUID

from sqlalchemy import Column, String, Table, Uuid, insert, select, update as sql_update
from sqlalchemy.ext.asyncio import AsyncSession

from library.<module>.exceptions import <Entity>NotFound
from library.<module>.models import <Entity>
from library.shared.adapters import metadata

<entity>_table = Table(
    "<entity_plural>",
    metadata,                          # <- always the shared MetaData instance
    Column("id", Uuid, primary_key=True),
    # ... other columns ...
)


class Sql<Entity>Repository:
    def __init__(self, session: AsyncSession):
        self._session = session

    def _row_to_<entity>(self, row: Any) -> <Entity>:
        entity = <Entity>(...)
        entity.id = row.id
        return entity

    async def find_by_id(self, id: UUID) -> <Entity> | None:
        row = (await self._session.execute(
            select(<entity>_table).where(<entity>_table.c.id == id)
        )).first()
        return self._row_to_<entity>(row) if row else None

    async def update(self, entity: <Entity>) -> None:
        stmt = (
            sql_update(<entity>_table)
            .where(<entity>_table.c.id == entity.id)
            .values(...)
            .returning(<entity>_table.c.id)
        )
        result = await self._session.execute(stmt)
        if result.scalar_one_or_none() is None:
            raise <Entity>NotFound(f"<Entity> {entity.id} not found")

    # ... create, delete, list_all, domain-specific queries ...
```

**Always use the shared `metadata`** so all tables register into one schema. **Always detect "0 rows affected" via `.returning(table.c.id) + scalar_one_or_none()`** — never `result.rowcount` (it forces a `# type: ignore`).

If the module also provides an **adapter for another module's port** (the asymmetric pattern), it goes in this same `repositories.py` — see `MemberCredentialVerifier` in [member/repositories.py](../../../library/member/repositories.py) or `LoanBookAvailability` in [loan/repositories.py](../../../library/loan/repositories.py).

### Step 8 — Generate use cases

One file per use case under `use_cases/<verb>_<entity>.py`. Each file contains BOTH the Command DTO and the UseCase class. See [`AddBookUseCase`](../../../library/book/use_cases/add_book.py):

```python
from dataclasses import dataclass

from library.<module>.exceptions import <ApplicationException>
from library.<module>.models import <Entity>
from library.<module>.ports import <Entity>Repository


@dataclass(frozen=True)
class <Verb><Noun>Command:
    # only fields the use case needs; not the HTTP shape
    ...


class <Verb><Noun>UseCase:
    def __init__(self, repo: <Entity>Repository, ...):
        self._repo = repo

    async def execute(self, command: <Verb><Noun>Command) -> <Entity>:
        ...
```

Use cases NEVER import from `repositories.py` or `api/`.

### Step 9 — Generate API (only if the module is exposed via HTTP)

Mirror [`book/api/`](../../../library/book/api/):

- `api/__init__.py` aggregates per-route routers via `include_router`. If the module's routes share an auth gate, declare it once on the aggregator's `APIRouter(dependencies=[Depends(get_verified_member)])` — see [`loan/api/__init__.py`](../../../library/loan/api/__init__.py).
- `api/dependencies.py` — feature-local DI providers (`get_<entity>_repo`, one per use case). Imports cross-cutting providers from `library.shared.api.dependencies`.
- `api/schemas.py` — the shared response shape (e.g., `<Entity>Response`) used by multiple routes.
- `api/routes/<verb>_<entity>.py` — one file per route, owning its own `APIRouter(prefix="/<entity_plural>", tags=["<entity>"])`, its request schema (Pydantic), and the handler.

### Step 10 — Wire cross-module port bridges (if any)

If the module **provides** an adapter for **another module's port** (e.g., your new `Recommendation` module provides an impl of `book.ports.SomeBookPort`), edit the composition root in [`library/shared/api/dependencies.py`](../../../library/shared/api/dependencies.py) to wire the bridge. Mirror the pattern of `get_credential_verifier` (auth port → member impl) or `get_book_availability` (book port → loan impl). Feature-private DI stays in the module's own `api/dependencies.py`.

### Step 11 — Register the router

In [`library/shared/api/main.py`](../../../library/shared/api/main.py), import the aggregated router and `app.include_router(...)`. Also register any custom exception handlers for the new module's `exceptions.py` classes.

### Step 12 — Verify

Run [`/verify`](../verify/SKILL.md). All six steps (pytest, ruff, mypy, codespell, pip-audit, pip-licenses) must pass clean.

## Reference shapes

- **Minimal (port + impl only):** [`notification/`](../../../library/notification/) — `models.py` + `ports.py` + one impl file. No use_cases, no api.
- **Standard CRUD:** [`book/`](../../../library/book/) — VO in models.py, full repository pattern with cache decorator, REST API.
- **Multi-aggregate:** [`loan/`](../../../library/loan/) — consumes Book and Member ports, no cache, no VOs, router has shared auth gate.
- **Identity / session:** [`member/`](../../../library/member/), [`auth/`](../../../library/auth/) — JWT issuer adapters co-located in `repositories.py`, custom security primitives in `api/security.py` (auth only).

## Do not

- ❌ Generate the skeleton without confirming scope with the human first
- ❌ Skip the test tree — modules and tests mirror each other
- ❌ Add `from library.<module>.repositories import ...` in `models.py`, `ports.py`, or `use_cases/`
- ❌ Forget to register the SQL table on the shared `metadata`
- ❌ Reintroduce `domain/` / `application/` / `infrastructure/` / `presentation/` subfolders — the project is deliberately flat
- ❌ Use `result.rowcount` for DML; always `.returning(table.c.id) + scalar_one_or_none()`
- ❌ Add cross-module imports in the wrong direction (see Dependency Rule in AGENTS.md)
