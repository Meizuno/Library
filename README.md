# Library — A Clean Architecture Example in Python

A library management system built as a deliberate exercise in **Clean Architecture**,
**Domain-Driven Design**, and **Hexagonal (Ports & Adapters)** patterns, organized
as a **modular monolith** with feature-based slices. The library domain (books, members,
loans) is a vehicle — the real subject is how to organize async Python code so that
business logic, persistence, transport, and infrastructure can evolve independently.

> 258 tests. Every architectural claim below is enforced by a test.

---

## Table of contents

- [The Dependency Rule, made concrete](#the-dependency-rule-made-concrete)
- [Project layout](#project-layout)
- [Core patterns demonstrated](#core-patterns-demonstrated)
- [Test pyramid](#test-pyramid)
- [Tech stack](#tech-stack)
- [Getting started](#getting-started)
- [HTTP API](#http-api)
- [Docker](#docker)
- [Architectural decisions worth highlighting](#architectural-decisions-worth-highlighting)
- [What this project deliberately does not do](#what-this-project-deliberately-does-not-do)

---

## The Dependency Rule, made concrete

The codebase is **sliced by bounded context** at the top level (`book/`, `member/`,
`loan/`), and **layered hexagonally** inside each slice:

```
                  ┌─────────────────────────────────────────────────┐
                  │  presentation/  ── HTTP (FastAPI)               │
                  │     ↓                                           │
                  │  application/   ── use cases, commands,         │
                  │     ↓              app-level exceptions         │
                  │  domain/        ── entities, value objects,     │
                  │                    repository protocols,        │
                  │                    domain exceptions            │
                  │     ↑                                           │
                  │  infrastructure/── SQL, Redis, cache,           │
                  │                    in-memory adapters           │
                  └─────────────────────────────────────────────────┘
                  applied independently inside book/, member/, loan/
```

**Source-code dependencies always point inward.** Within any slice,
[`<feature>/domain/`](library/book/domain/) imports nothing from `application/`,
`infrastructure/`, or `presentation/`. `application/` imports only from `domain/`.
`infrastructure/` implements `domain/` protocols. `presentation/` orchestrates everything
from the outside.

**Cross-slice imports are allowed where they are natural and one-way.** The `loan` slice
imports `BookRepository`, `MemberRepository`, and a few exceptions from `book/` and
`member/`, because borrowing a book is a use case that genuinely spans three aggregates.
`book/` and `member/` do not know about `loan/`.

[`shared/`](library/shared/) holds genuinely cross-cutting infrastructure (`Clock` port,
cache adapters, shared SQL `MetaData`, config, structlog setup) and the composition root
(FastAPI app entry point).

This is enforced not by tooling but by discipline + tests. Try violating it and
contract tests start failing in unintuitive ways.

---

## Project layout

```
library/
├── book/                          # Bounded context: books
│   ├── domain/
│   │   ├── model.py               # Book (entity)
│   │   ├── value_objects.py       # ISBN (immutable, validated)
│   │   ├── repository.py          # BookRepository  ← Protocol (port)
│   │   └── exceptions.py          # BookNotFound, BookNotAvailable
│   ├── application/
│   │   ├── commands.py            # AddBookCommand
│   │   ├── exceptions.py          # BookAlreadyExists
│   │   └── use_cases/             # One file per use case (SRP)
│   │       ├── add_book.py
│   │       ├── read_book.py
│   │       ├── list_books.py
│   │       └── delete_book.py
│   ├── infrastructure/
│   │   ├── in_memory_repository.py   # InMemoryBookRepository
│   │   ├── sql_table.py              # books_table (uses shared MetaData)
│   │   ├── sql_repository.py         # SqlBookRepository
│   │   └── cached_repository.py      # CachedBookRepository (Decorator)
│   └── presentation/
│       └── api/
│           ├── schemas.py         # Pydantic DTOs (BookCreate, BookResponse)
│           ├── dependencies.py    # get_book_repo, get_*_use_case
│           └── router.py          # /books endpoints
│
├── member/                        # Same shape: Member, Email, MemberRepository, …
├── loan/                          # Same shape: Loan, LoanRepository,
│                                  # BorrowBookUseCase, ReturnBookUseCase
│                                  # (no cached repo, no value objects of its own)
│
└── shared/                        # Cross-cutting code
    ├── config.py                  # Pydantic Settings (fail-fast on missing env)
    ├── logging_config.py          # structlog + stdlib bridge
    ├── domain/
    │   └── exceptions.py          # DomainError (base)
    ├── application/
    │   ├── clock.py               # Clock Protocol (port)
    │   └── exceptions.py          # ApplicationError (base)
    ├── infrastructure/
    │   ├── clock.py               # SystemClock (real wall clock)
    │   ├── sql_metadata.py        # shared MetaData() instance
    │   └── cache/
    │       ├── protocol.py        # Cache Protocol (internal port)
    │       ├── redis.py           # RedisCache with graceful degradation
    │       └── in_memory.py       # InMemoryCache with LRU eviction
    └── presentation/              # Composition root
        └── api/
            ├── main.py            # FastAPI app, lifespan, exception handlers
            ├── dependencies.py    # get_settings, get_session, get_redis, get_cache, get_clock
            └── middleware.py      # request_logging_middleware (structlog)

tests/                             # Mirrors the source tree 1:1
├── conftest.py                    # Cross-feature fixtures (valid_*, clock, client)
├── book/{domain, application, infrastructure, presentation/api/}
├── member/{…}
├── loan/{…}
└── shared/infrastructure/{test_clock.py, cache/test_in_memory.py}
```

Browse the source: [`library/`](library/) · [`tests/`](tests/).

---

## Core patterns demonstrated

### Repository Pattern (Ports & Adapters)

[`BookRepository`](library/book/domain/repository.py),
[`MemberRepository`](library/member/domain/repository.py), and
[`LoanRepository`](library/loan/domain/repository.py) are `typing.Protocol`
classes living in each feature's `domain/`. Three concrete implementations live in
the feature's `infrastructure/`: `InMemory*`, `Sql*`, plus a `Cached*` decorator
(books and members only). Use cases depend only on the protocol; they have no idea
which backend they're talking to.

A single contract test suite is parametrized over every implementation
([`tests/book/infrastructure/conftest.py`](tests/book/infrastructure/conftest.py)):

```python
@pytest.fixture(params=["in_memory", "sql", "cache_redis", "cache_in_memory"])
async def empty_book_repo(request, sql_book_repo):
    ...
```

If a new implementation passes the contract suite, it is provably substitutable
(LSP). 106 contract tests run across the three feature repos × multiple backends.

### Decorator Pattern (CachedBookRepository)

[`CachedBookRepository`](library/book/infrastructure/cached_repository.py) wraps any
`BookRepository` and adds Redis caching to `find_by_id`. The cache layer itself is
abstracted behind a `Cache` protocol
([`shared/infrastructure/cache/protocol.py`](library/shared/infrastructure/cache/protocol.py))
with two implementations:
[`RedisCache`](library/shared/infrastructure/cache/redis.py) (network) and
[`InMemoryCache`](library/shared/infrastructure/cache/in_memory.py) (LRU). The decorator
works against any cache, the cache works against any backend. DIP applied recursively.

### Clock Pattern (testable time)

Use cases never call `datetime.now()` directly. They depend on a `Clock` protocol
([`shared/application/clock.py`](library/shared/application/clock.py)) injected
through the constructor. Production uses
[`SystemClock`](library/shared/infrastructure/clock.py); tests use a `FakeClock`
returning a fixed time. Tests can assert exact timestamps, not "within a few
seconds of now".

### Repository per Aggregate, ID references between aggregates

[`Loan`](library/loan/domain/model.py) references its book and member by `UUID`, not
by object reference. Each aggregate is loaded and saved independently. This keeps
consistency boundaries explicit and aggregates persistable in isolation — and it is
what makes the `loan/` slice possible without `book/` and `member/` having to know
about it.

### Configuration as code (fail-fast Pydantic Settings)

From [`library/shared/config.py`](library/shared/config.py):

```python
class Settings(BaseSettings):
    database_url: str          # required — startup fails without it
    redis_url: str             # required
    cache_ttl: int = 300
    log_level: str = "INFO"
    log_format: Literal["console", "json"] = "console"

    model_config = SettingsConfigDict(env_file=".env", extra="forbid")
```

Required env vars are validated at import time, not on first use. Typos in env names
(`DATABSE_URL`) fail loudly thanks to `extra="forbid"`.

### Structured logging with request context

`structlog` is configured in
[`library/shared/logging_config.py`](library/shared/logging_config.py) with
`contextvars.merge_contextvars`. The HTTP middleware
([`shared/presentation/api/middleware.py`](library/shared/presentation/api/middleware.py))
binds `request_id`, `method`, `path` once per request, and every downstream log call —
including cache failures three layers deep — automatically inherits that context.
Logs render as colorized console output in development, JSON in production.

---

## Test pyramid

| Layer | Count | What it proves |
|-------|------:|----------------|
| [Domain](tests/) (book + member + loan) | 63 | Business rules without any I/O |
| [Application (use cases)](tests/) | 27 | Orchestration logic with in-memory fakes, no I/O |
| [Infrastructure contract](tests/) | 106 | Every repository implementation satisfies its protocol (LSP) across 4 backends |
| [Cache behavior](tests/) | 12 | Decorator caches on read, invalidates on write (book + member) |
| [In-memory cache](tests/shared/infrastructure/cache/test_in_memory.py) | 11 | LRU eviction, move-to-end on access |
| [Clock](tests/shared/infrastructure/test_clock.py) | 2 | SystemClock satisfies the Clock protocol |
| [API end-to-end](tests/) | 18 | HTTP ↔ use case translation, exception → status mapping |

Each level tests one rung of abstraction; almost no duplication between levels.

---

## Tech stack

- **Python 3.12+** (async/await throughout)
- **FastAPI** — driving HTTP adapter
- **SQLAlchemy 2.x Core** (not ORM) — dialect-agnostic SQL
- **asyncpg** / **aiosqlite** — async database drivers
- **redis-py** (async) — cache adapter
- **pydantic + pydantic-settings** — schemas and configuration
- **pytest + pytest-asyncio** — test runner
- **httpx + ASGITransport** — in-process HTTP testing
- **fakeredis** — in-process Redis for cache tests
- **structlog** — structured, context-aware logging

Pinned versions live in [`pyproject.toml`](pyproject.toml).

---

## Getting started

### Prerequisites

- Python 3.12+
- (Optional, for full local run) PostgreSQL and Redis

### Install

```sh
python -m venv .venv
.venv\Scripts\activate           # Windows
# source .venv/bin/activate      # macOS / Linux

pip install -e ".[dev]"
```

### Configure

Copy [`.env.example`](.env.example) to `.env` and fill in real values:

```sh
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/library
REDIS_URL=redis://localhost:6379/0
CACHE_TTL=300
LOG_LEVEL=INFO
LOG_FORMAT=console
```

For quick local experimentation without Postgres, you can point at a file:

```sh
DATABASE_URL=sqlite+aiosqlite:///./library.db
```

### Run tests

```sh
pytest
```

### Run the API

```sh
uvicorn library.shared.presentation.api.main:app --reload
```

Then open `http://localhost:8000/docs` for the interactive Swagger UI.

---

## HTTP API

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/books` | List all books |
| `POST` | `/books` | Add a book (201 / 409 / 422) |
| `GET` | `/books/{id}` | Read a book (200 / 404) |
| `DELETE` | `/books/{id}` | Delete a book (204 / 404) |
| `GET` | `/members` | List all members |
| `POST` | `/members` | Register a member (201 / 409 / 422) |
| `GET` | `/members/{id}` | Read a member (200 / 404) |
| `DELETE` | `/members/{id}` | Delete a member (204 / 404) |
| `POST` | `/loans` | Borrow a book (201 / 404 / 409) |
| `POST` | `/loans/{id}/return` | Return a book (200 / 404 / 422) |
| `GET` | `/health` | Liveness probe |

Domain exceptions are mapped to HTTP statuses centrally in
[`shared/presentation/api/main.py`](library/shared/presentation/api/main.py):

```python
BookNotFound       → 404
MemberNotFound     → 404
LoanNotFound       → 404
BookAlreadyExists  → 409
MemberAlreadyExists→ 409
BookNotAvailable   → 409
ValueError         → 422   # invalid VO / domain invariant
```

Routers (one per feature, under [`<feature>/presentation/api/router.py`](library/book/presentation/api/router.py))
never `try/except` — they let exceptions bubble up to the handlers.

---

## Docker

A production-ready multi-stage [`Dockerfile`](Dockerfile) is provided.
[`.dockerignore`](.dockerignore) keeps the build context minimal — tests,
caches, IDE configs, and `.env` files never reach the build.

### What the image looks like

- **Multi-stage build** — a `builder` stage compiles dependencies into a
  virtualenv at `/opt/venv`. Only the venv is copied into the final image, so
  the runtime layer contains no `build-essential`, no source `.py` files for
  the package (the package is installed into the venv), and no pip cache.
- **Non-root user** — the process runs as user `app`, not as root. Even
  with a compromise inside the container, escalation requires a separate
  exploit.
- **`python:3.12-slim`** base — small (~50 MB) and glibc-based, compatible
  with `asyncpg` and other binary wheels that Alpine sometimes breaks.
- **Healthcheck** — Docker hits `/health` every 30 s. Orchestrators
  (compose, Kubernetes) can use it to decide whether the container is alive.
- **`PYTHONUNBUFFERED=1`** — logs go straight to stdout, so `docker logs`
  shows them in real time (essential for structlog's JSON output).

### Build

```sh
docker build -t library:latest .
```

### Run

The image expects `DATABASE_URL` and `REDIS_URL` from the environment — there
is no `.env` baked into the image (that would be a secret-leakage anti-pattern).

```sh
docker run --rm -p 8000:8000 \
    -e DATABASE_URL="sqlite+aiosqlite:///./library.db" \
    -e REDIS_URL="redis://host.docker.internal:6379/0" \
    -e CACHE_TTL=300 \
    -e LOG_LEVEL=INFO \
    -e LOG_FORMAT=json \
    library:latest
```

For real deployments, pass secrets via your orchestrator's secret store
(Kubernetes `Secret`, Docker Swarm `secret`, etc.) — never bake them into
the image or commit them to git.

Then `curl http://localhost:8000/health` should return `"OK"`, and
`/docs` is reachable as usual.

### Local development with docker-compose

A [`docker-compose.yml`](docker-compose.yml) brings up the app together
with Postgres and Redis, configured for an iterative dev loop:

```sh
docker compose up --build
```

Then `http://localhost:8000/docs` is live, Postgres listens on `5432`,
Redis on `6379`.

Key details:

- **Hot reload** — source is mounted as `./library:/app/library`, and
  `PYTHONPATH=/app` makes the mounted directory win over the version
  baked into site-packages. Edit a file on the host → uvicorn picks
  it up inside the container without rebuilding the image.
- **`depends_on: condition: service_healthy`** — the app waits for
  Postgres `pg_isready` and Redis `PING` before starting, so the
  first request doesn't fail on a not-yet-ready dependency.
- **Persistent Postgres data** — a named volume `postgres_data` keeps
  the database between `compose down` / `compose up`. To wipe it:
  `docker compose down -v`.
- **`LOG_FORMAT=console`, `LOG_LEVEL=DEBUG`** — overrides for
  human-readable, verbose dev logs. Production should set
  `LOG_FORMAT=json` and `LOG_LEVEL=INFO` via the deployment env.

For production deployments, you'd typically run only the `app`
service from this file (Postgres and Redis come from managed
services), or use a separate `docker-compose.prod.yml` without
the source mount and with `--reload` removed.

---

## Architectural decisions worth highlighting

### Hybrid: hexagonal layers inside feature folders

A classic hexagonal codebase groups by *technical layer* — one `domain/`, one
`application/`, one `infrastructure/`, one `api/`. That answers "what kind of code
is this?" but forces a developer working on "books" to touch five or six folders.

A pure Vertical-Slice Architecture goes the other way and slices per use case —
`book/add_book/`, `book/read_book/`, etc. — but at this project's size that produces
many almost-empty per-slice `domain/` and `infrastructure/` folders that just
re-export shared types.

This codebase picks the **middle**: slice by bounded context (`book/`, `member/`,
`loan/`), keep hexagonal layers inside each slice. You get the "everything about
books is in one place" win, you keep hexagonal discipline, and the layer folders
inside a slice are actually populated. Going further to per-use-case slices is left
as a path you take when individual use cases start having genuinely independent
schemas, persistence concerns, or owners — not before.

### `shared/` for cross-cutting code, not a junk drawer

[`shared/`](library/shared/) holds only code that is **provably cross-cutting**:
the `Clock` port (every use case that needs time), the `Cache` protocol (used by
multiple features' cached repositories), shared SQL `MetaData` (so all tables register
into one schema), the FastAPI composition root, config,
and logging. Domain models, repositories, and use cases all live in their feature
folder. The rule is: if exactly one feature uses it, it belongs in that feature.

### Cross-slice imports are explicit and one-way

The `loan` slice's
[`BorrowBookUseCase`](library/loan/application/use_cases/borrow_book.py) imports
`BookRepository`, `MemberRepository`, and `BookNotAvailable` / `BookNotFound` /
`MemberNotFound` from its sibling slices. That is correct — borrowing a book is a
multi-aggregate operation. The reverse is enforced not by tooling but by review:
`book/` and `member/` must not import from `loan/`. This is the modular-monolith
equivalent of "`loan` is downstream of `book` and `member`."

### Repository protocols live in `<feature>/domain/`, not `<feature>/application/`

The repository expresses what the domain **demands** from persistence, in domain
language (`find_by_isbn`, not `SELECT * FROM books`). It is the domain's outward-facing
port. Implementations belong outside the domain; the interface belongs inside it. See
[`book/domain/repository.py`](library/book/domain/repository.py).

### `Cache` protocol lives in `shared/infrastructure/`, not in any domain

Caching is a runtime optimization — domain entities know nothing about it. The
protocol ([`shared/infrastructure/cache/protocol.py`](library/shared/infrastructure/cache/protocol.py))
is consumed only by other infrastructure code (`CachedBookRepository`,
`CachedMemberRepository`). It is an *internal* abstraction of the infrastructure
layer, not a domain concern, and it is shared because the same `Cache` instance backs
both feature decorators.

### Pydantic schemas in `<feature>/presentation/api/`, never in `<feature>/domain/`

[`BookCreate` and `BookResponse`](library/book/presentation/api/schemas.py) are HTTP
DTOs. They translate between HTTP and domain. Validation of HTTP-format concerns
(required fields, JSON types) happens in the schema; validation of domain invariants
(non-empty title, valid ISBN format) happens in the
[entity](library/book/domain/model.py). No duplication — the API schema is intentionally
permissive, the domain rejects invalid state.

### Session-per-request, not Unit of Work

A `UnitOfWork` abstraction was introduced and then removed. For this project,
FastAPI's per-request dependency cache plus `get_session` in
[`shared/presentation/api/dependencies.py`](library/shared/presentation/api/dependencies.py)
(which commits on success, rolls back on exception) already provide transactional
consistency across multiple repositories — the same session is shared automatically.
A separate `UnitOfWork` layer would have duplicated this without adding value.

The lesson: **a pattern earns its place by solving present pain, not by
appearing in textbooks.**

### Use cases are classes, not functions

`AddBookUseCase`, `BorrowBookUseCase`, etc.
(`<feature>/application/use_cases/`) each have a single `execute(command)` method.
Why classes for what could be functions?

- Constructor injection of dependencies (repositories, clock).
- One file per use case → easy to find, hard to merge-conflict.
- The class is a stable surface even when the algorithm changes.
- Maps naturally to the Command pattern (GoF).

### CRUD use cases get individual repositories; multi-aggregate use cases too

The simple use cases ([`AddBookUseCase`](library/book/application/use_cases/add_book.py),
[`DeleteBookUseCase`](library/book/application/use_cases/delete_book.py)) take one
repository. [`BorrowBookUseCase`](library/loan/application/use_cases/borrow_book.py)
takes three (`books`, `members`, `loans`) plus a `Clock`. FastAPI's DI cache ensures
they share the same SQL session within a request, so atomicity is preserved without
extra abstractions.

---

## What this project deliberately does **not** do

These were considered and intentionally left out:

- **Per-use-case slicing** — see the architecture decision above. Per-entity slices
  hit the cost/benefit sweet spot at this size; per-use-case adds folder noise without
  proportional payoff.
- **CQRS** — read and write models are the same. No projection layer.
- **Event sourcing** — state is the current value of fields, not a log of events.
- **Authentication / authorization** — orthogonal to the architecture lesson.
- **Pagination / filtering on list endpoints** — outside the demonstration scope.
- **Generic `BaseEntity`** — premature abstraction. Each entity defines its
  own `__eq__`/`__hash__` by `id`. Three lines × three entities beats one
  invisible inheritance hierarchy.
- **Unit of Work** — see above. Removed after measuring that session-per-request
  carried the same weight.

---

## License

MIT.
