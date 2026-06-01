---
name: add-slice
description: Generate a new bounded-context slice with full hexagonal layer skeleton (domain, application, infrastructure, presentation).
---

# Add Bounded-Context Slice

When the human says "add a new slice X" or "add bounded context X" (e.g., "add `reservation/`", "add `payment/`"), follow this skill to create the **complete folder + file skeleton**.

This is a **bigger** task than `/add-use-case`. Only use this when introducing a **new aggregate root** with its own lifecycle, not a new operation on an existing one.

## Pre-flight

1. Read [AGENTS.md](../../../AGENTS.md) — confirm slice structure rules and cross-slice import policy.
2. Read existing slices as reference:
   - [`book/`](../../../library/book/) — simplest (no cross-slice deps)
   - [`member/`](../../../library/member/) — has VOs (Email, Password), credential adapters
   - [`loan/`](../../../library/loan/) — multi-aggregate (uses Book, Member ports)
   - [`auth/`](../../../library/auth/) — defines ports consumed by other slices
   - [`notification/`](../../../library/notification/) — minimal (port + impl, no use case in itself)

## Workflow

### Step 1 — Confirm scope with the human

Before generating skeleton, ask:

- What's the **aggregate root** for this slice? (entity name)
- What **VOs** does it own? (e.g., Reservation owns `ReservationCode`, `ReservationStatus`)
- What **use cases** are needed initially? List them as `<verb>_<noun>`.
- Does it **consume ports** from other slices? Which?
- Does it **expose ports** for other slices to consume?
- Will it have a **REST API**, or is it driven by other slices only (like `notification/`)?
- Cache decorator? (Books and Members have it; Loans does not.)
- Soft delete on this aggregate? (Books and Members do; Loans and RefreshTokens do not.) See `deleted_at` pattern in [`books_table`](../../../library/book/infrastructure/sql_table.py) / [`members_table`](../../../library/member/infrastructure/sql_table.py).

**Wait for human confirmation. Do not generate the skeleton without it.**

### Step 2 — Generate folder skeleton

```
library/<slice>/
├── __init__.py
├── domain/
│   ├── __init__.py
│   ├── model.py               # Entity (e.g., Reservation)
│   ├── value_objects.py       # if any VOs
│   ├── repository.py          # <Entity>Repository protocol
│   ├── services.py            # ports consumed by this slice (optional)
│   └── exceptions.py          # <Entity>NotFound, invariant violations
├── application/
│   ├── __init__.py
│   ├── commands.py            # frozen dataclass DTOs
│   ├── exceptions.py          # <Entity>AlreadyExists, policy violations
│   └── use_cases/
│       ├── __init__.py
│       └── <each use case>.py
├── infrastructure/
│   ├── __init__.py
│   ├── sql_table.py           # books_table-style declaration on shared MetaData
│   ├── sql_repository.py
│   └── cached_repository.py   # only if caching is decided
└── presentation/
    ├── __init__.py
    └── api/
        ├── __init__.py
        ├── schemas.py         # Pydantic <Entity>Create, <Entity>Response
        ├── dependencies.py    # FastAPI providers for use cases
        └── router.py          # APIRouter
```

Also create the **test tree** mirroring source:

```
tests/<slice>/
├── __init__.py
├── domain/
│   ├── __init__.py
│   ├── test_model.py
│   └── test_value_objects.py
├── application/
│   ├── __init__.py
│   └── test_<each use case>.py
├── infrastructure/
│   ├── __init__.py
│   ├── conftest.py            # parametrized repository fixture (sql, optionally cache_redis / cache_in_memory)
│   └── test_repository_contract.py
└── presentation/
    └── api/
        ├── __init__.py
        └── test_<each endpoint>.py
```

### Step 3 — Generate the entity (domain/model.py)

Mirror [`Book`](../../../library/book/domain/model.py) or [`Member`](../../../library/member/domain/model.py):

```python
from uuid import UUID, uuid4
from dataclasses import dataclass, field


@dataclass(kw_only=True)
class <Entity>:
    id: UUID = field(init=False, default_factory=uuid4)
    # ... fields ...

    def __post_init__(self):
        # validation only — no I/O
        ...

    def __eq__(self, other):
        if not isinstance(other, <Entity>):
            return NotImplemented
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)

    # state transitions as methods (e.g., mark_verified, cancel)
```

### Step 4 — Generate VOs (domain/value_objects.py)

Mirror [`ISBN`](../../../library/book/domain/value_objects.py) or [`Email`](../../../library/member/domain/value_objects.py):

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class <ValueObject>:
    value: str

    def __post_init__(self):
        # validation
        # normalization via object.__setattr__ if frozen
        ...
```

### Step 5 — Generate the repository protocol (domain/repository.py)

Mirror [`BookRepository`](../../../library/book/domain/repository.py):

```python
from typing import Protocol
from uuid import UUID
from library.<slice>.domain.model import <Entity>


class <Entity>Repository(Protocol):
    async def find_by_id(self, id: UUID) -> <Entity> | None: ...
    async def create(self, entity: <Entity>) -> None: ...
    async def update(self, entity: <Entity>) -> None: ...
    async def delete(self, id: UUID) -> None: ...
    async def list_all(self) -> list[<Entity>]: ...
```

**`create` and `update` are separate** — no upserts. Add domain-specific queries (`find_by_email`, `find_active_due_on`) as needed.

### Step 6 — Generate domain exceptions

```python
# library/<slice>/domain/exceptions.py
from library.shared.domain.exceptions import DomainError


class <Entity>NotFound(DomainError):
    pass


class <Entity>InvariantViolation(DomainError):
    pass
```

Application exceptions go in `application/exceptions.py`, inheriting from `shared.application.exceptions.ApplicationError`.

### Step 7 — Generate SQL table + repository

`infrastructure/sql_table.py`:

```python
from sqlalchemy import Column, String, ...
from sqlalchemy.dialects.postgresql import UUID
from library.shared.infrastructure.sql_metadata import metadata

<entity>_table = Table(
    "<entity_plural>",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    # ...
)
```

**Always use the shared `metadata`** so all tables register into one schema.

### Step 8 — Wire composition root

Edit [`library/shared/presentation/api/dependencies.py`](../../../library/shared/presentation/api/dependencies.py) to:

1. Add `get_<entity>_repo` (returns the `Sql<Entity>Repository`, optionally wrapped by `Cached<Entity>Repository`)
2. Add `get_<verb>_<noun>_use_case` for each use case
3. Register the router (in `shared/presentation/api/main.py`)

Tests override `get_<entity>_repo` automatically through the `<entity>_repo` fixture in [`tests/conftest.py`](../../../tests/conftest.py) — there is no separate in-memory backend; SQLite `:memory:` plays both roles.

### Step 10 — Update README

Add the new slice to:
- "Project layout" section (folder tree)
- "Cross-slice imports" if applicable
- "HTTP API" table if API endpoints added

### Step 11 — Verify

```sh
pytest -W error
pylint library tests
```

Both must pass clean. Pylint must score **10.00/10**. See `/verify` skill.

## Reference

Smallest reference slice: [`notification/`](../../../library/notification/) — has only domain (port + VO) and infrastructure (one impl). No use cases of its own, no API. Adopt this shape if your slice is a service-port-only.

Standard reference: [`book/`](../../../library/book/) — full CRUD with VO, multi-impl repository, cache decorator, API.

Multi-aggregate reference: [`loan/`](../../../library/loan/) — consumes Book and Member ports, no cache, no VOs.

## Do not

- ❌ Generate the skeleton without confirming scope with the human first
- ❌ Skip the test tree — slices and tests are 1:1 mirrors
- ❌ Add `from library.<slice>.infrastructure import ...` in `domain/` or `application/`
- ❌ Forget to register the SQL table on the shared `metadata`
- ❌ Add the slice to `library/application/use_cases/` (root legacy) — use `library/<slice>/`
- ❌ Add cross-slice imports in the wrong direction (see Dependency Rule in AGENTS.md)
