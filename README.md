# Library — A Clean Architecture Example in Python

A library management system built as a deliberate exercise in **Clean Architecture**,
**Domain-Driven Design**, and **Hexagonal (Ports & Adapters)** patterns. The library
domain (books, members, loans) is a vehicle — the real subject is how to organize
async Python code so that business logic, persistence, transport, and infrastructure
can evolve independently.

> 239 tests. Every architectural claim below is enforced by a test.

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

```
                  ┌────────────────────────────────────────────┐
                  │  api/  ── HTTP, FastAPI, Pydantic schemas  │
                  │     ↓                                      │
                  │  application/  ── use cases, commands,     │
                  │     ↓             Clock port               │
                  │  domain/  ── entities, value objects,      │
                  │               repository protocols,        │
                  │               domain exceptions            │
                  │     ↑                                      │
                  │  infrastructure/  ── SQL, Redis, cache,    │
                  │                      in-memory adapters    │
                  └────────────────────────────────────────────┘
```

**Source-code dependencies always point inward.** [`domain/`](library/domain/) imports
nothing from [`application/`](library/application/),
[`infrastructure/`](library/infrastructure/), or [`api/`](library/api/).
[`application/`](library/application/) imports only from
[`domain/`](library/domain/). [`infrastructure/`](library/infrastructure/)
implements [`domain/`](library/domain/) protocols.
[`api/`](library/api/) orchestrates everything from the outside.

This is enforced not by tooling but by discipline + tests. Try violating it and
contract tests start failing in unintuitive ways.

---

## Project layout

```
library/
├── domain/                      # Business core — knows nothing else
│   ├── models.py                # Book, Member, Loan (entities)
│   ├── value_objects.py         # ISBN, Email (immutable, validated)
│   ├── repositories.py          # BookRepository, MemberRepository,
│   │                            #   LoanRepository  ← Protocols (ports)
│   └── exceptions.py            # BookNotFound, BookNotAvailable, ...
│
├── application/                 # Orchestration — uses domain abstractions
│   ├── commands.py              # AddBookCommand, BorrowBookCommand, ...
│   ├── use_cases/               # One file per use case (SRP)
│   │   ├── add_book.py
│   │   ├── borrow_book.py
│   │   ├── return_book.py
│   │   └── ...
│   ├── clock.py                 # Clock Protocol (port)
│   └── exceptions.py            # ApplicationError, BookAlreadyExists, ...
│
├── infrastructure/              # Adapters — concrete tech, swappable
│   ├── in_memory_repositories.py    # InMemoryBook/Member/LoanRepository
│   ├── clock.py                     # SystemClock (real wall clock)
│   ├── sql/
│   │   ├── tables.py                # SQLAlchemy Core table definitions
│   │   ├── book_repository.py       # SqlBookRepository
│   │   ├── member_repository.py
│   │   └── loan_repository.py
│   └── cached/
│       ├── protocol.py              # Cache Protocol (internal port)
│       ├── redis_cache.py           # RedisCache with graceful degradation
│       ├── in_memory.py             # InMemoryCache with LRU eviction
│       ├── book_repository.py       # CachedBookRepository (Decorator)
│       └── member_repository.py
│
├── api/                         # Driving adapter — HTTP
│   ├── main.py                  # FastAPI app + lifespan + exception handlers
│   ├── dependencies.py          # DI providers: get_book_repo, get_clock, ...
│   ├── middleware.py            # request_logging_middleware (structlog)
│   ├── routers/                 # One file per entity
│   │   ├── book.py
│   │   ├── member.py
│   │   └── loan.py
│   └── schemas/                 # Pydantic DTOs (NOT domain models)
│       ├── book.py
│       ├── member.py
│       └── loan.py
│
├── config.py                    # Pydantic Settings (fail-fast on missing env)
└── logging_config.py            # structlog + stdlib bridge

tests/
├── domain/                      # Entity invariants, value object validation
├── infrastructure/              # Contract tests parametrized over impls
├── application/                 # Use case orchestration (in-memory only)
└── api/                         # HTTP end-to-end via httpx ASGITransport
```

Browse the source: [`library/`](library/) · [`tests/`](tests/).

---

## Core patterns demonstrated

### Repository Pattern (Ports & Adapters)

`BookRepository`, `MemberRepository`, `LoanRepository` are `typing.Protocol`
classes in [`domain/repositories.py`](library/domain/repositories.py).
Three concrete implementations live in [`infrastructure/`](library/infrastructure/):
[`InMemory*`](library/infrastructure/in_memory_repositories.py),
[`Sql*`](library/infrastructure/sql/), plus a
[`Cached*`](library/infrastructure/cached/) decorator. Use cases depend
only on the protocol; they have no idea which backend they're talking to.

A single contract test suite is parametrized over every implementation
([`tests/infrastructure/conftest.py`](tests/infrastructure/conftest.py)):

```python
@pytest.fixture(params=["in_memory", "sql", "cache_redis", "cache_in_memory"])
async def empty_book_repo(request, sql_book_repo):
    ...
```

If a new implementation passes the contract suite, it is provably substitutable
(LSP). 78 contract tests run against 4 backends.

### Decorator Pattern (CachedBookRepository)

[`CachedBookRepository`](library/infrastructure/cached/book_repository.py)
wraps any `BookRepository` and adds Redis caching to `find_by_id`. The cache layer
itself is abstracted behind a `Cache` protocol
([`cached/protocol.py`](library/infrastructure/cached/protocol.py))
with two implementations:
[`RedisCache`](library/infrastructure/cached/redis_cache.py) (network)
and [`InMemoryCache`](library/infrastructure/cached/in_memory.py) (LRU).
The decorator works against any cache, the cache works against any backend.
DIP applied recursively.

### Clock Pattern (testable time)

Use cases never call `datetime.now()` directly. They depend on a `Clock` protocol
([`application/clock.py`](library/application/clock.py)) injected through
the constructor. Production uses
[`SystemClock`](library/infrastructure/clock.py); tests use a `FakeClock`
returning a fixed time. Tests can assert exact timestamps, not "within a few
seconds of now".

### Repository per Aggregate, ID references between aggregates

[`Loan`](library/domain/models.py) references its book and member by
`UUID`, not by object reference. Each aggregate is loaded and saved
independently. This keeps consistency boundaries explicit and aggregates
persistable in isolation.

### Configuration as code (fail-fast Pydantic Settings)

From [`library/config.py`](library/config.py):

```python
class Settings(BaseSettings):
    database_url: str          # required — startup fails without it
    redis_url: str             # required
    cache_ttl: int = 300
    log_level: str = "INFO"
    log_format: Literal["console", "json"] = "console"

    model_config = SettingsConfigDict(env_file=".env", extra="forbid")
```

Required env vars are validated at import time, not on first use. Typos
in env names (`DATABSE_URL`) fail loudly thanks to `extra="forbid"`.

### Structured logging with request context

`structlog` is configured in
[`library/logging_config.py`](library/logging_config.py) with
`contextvars.merge_contextvars`. The HTTP middleware
([`api/middleware.py`](library/api/middleware.py)) binds `request_id`,
`method`, `path` once per request, and every downstream log call — including
cache failures three layers deep — automatically inherits that context. Logs
render as colorized console output in development, JSON in production.

---

## Test pyramid

| Layer | Count | What it proves |
|-------|------:|----------------|
| [Domain](tests/domain/) | 63 | Business rules without any I/O |
| [Infrastructure contract](tests/infrastructure/test_repositories.py) | ~90 | Every repository implementation satisfies its protocol (LSP) |
| [Cache behavior](tests/infrastructure/test_cached_repositories.py) | 12 | Decorator caches on read, invalidates on write |
| [In-memory cache](tests/infrastructure/test_in_memory_cache.py) | 11 | LRU eviction, move-to-end on access |
| [Use cases](tests/application/) | 35 | Orchestration logic with in-memory fakes, no I/O |
| [API end-to-end](tests/api/) | 28 | HTTP ↔ use case translation, exception → status mapping |

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
uvicorn library.api.main:app --reload
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
[`api/main.py`](library/api/main.py):

```python
BookNotFound       → 404
MemberNotFound     → 404
LoanNotFound       → 404
BookAlreadyExists  → 409
MemberAlreadyExists→ 409
BookNotAvailable   → 409
ValueError         → 422   # invalid VO / domain invariant
```

Routers ([`api/routers/`](library/api/routers/)) never `try/except` —
they let exceptions bubble up to the handlers.

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

### Repository protocols live in `domain/`, not `application/`

The repository expresses what the domain **demands** from persistence,
in domain language (`find_by_isbn`, not `SELECT * FROM books`). It is the
domain's outward-facing port. Implementations belong outside the domain;
the interface belongs inside it. See
[`domain/repositories.py`](library/domain/repositories.py).

### `Cache` protocol lives in `infrastructure/`, not `domain/`

Caching is a runtime optimization — domain entities know nothing about it.
The protocol ([`cached/protocol.py`](library/infrastructure/cached/protocol.py))
is consumed only by other infrastructure code
([`CachedBookRepository`](library/infrastructure/cached/book_repository.py)).
It is an *internal* abstraction of the infrastructure layer, not a domain concern.

### Pydantic schemas in `api/`, never in `domain/`

[`BookCreate` and `BookResponse`](library/api/schemas/book.py) are HTTP DTOs.
They translate between HTTP and domain. Validation of HTTP-format concerns (required
fields, JSON types) happens in the schema; validation of domain invariants
(non-empty title, valid ISBN format) happens in the
[entity](library/domain/models.py). No duplication — the API schema is
intentionally permissive, the domain rejects invalid state.

### Session-per-request, not Unit of Work

A `UnitOfWork` abstraction was introduced and then removed. For this project,
FastAPI's per-request dependency cache plus `get_session` in
[`api/dependencies.py`](library/api/dependencies.py) (which commits on
success, rolls back on exception) already provide transactional consistency
across multiple repositories — the same session is shared automatically.
A separate `UnitOfWork` layer would have duplicated this without adding value.

The lesson: **a pattern earns its place by solving present pain, not by
appearing in textbooks.**

### Use cases are classes, not functions

`AddBookUseCase`, `BorrowBookUseCase`, etc.
([`application/use_cases/`](library/application/use_cases/)) each have a
single `execute(command)` method. Why classes for what could be functions?

- Constructor injection of dependencies (repositories, clock).
- One file per use case → easy to find, hard to merge-conflict.
- The class is a stable surface even when the algorithm changes.
- Maps naturally to the Command pattern (GoF).

### CRUD use cases get individual repositories; multi-aggregate use cases too

The simple use cases ([`AddBookUseCase`](library/application/use_cases/add_book.py),
[`DeleteBookUseCase`](library/application/use_cases/delete_book.py))
take one repository.
[`BorrowBookUseCase`](library/application/use_cases/borrow_book.py) takes
three (`books`, `members`, `loans`) plus a `Clock`. FastAPI's DI cache ensures
they share the same SQL session within a request, so atomicity is preserved
without extra abstractions.

---

## What this project deliberately does **not** do

These were considered and intentionally left out:

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
