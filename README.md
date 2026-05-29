# Library — A Clean Architecture Example in Python

A library management system built as a deliberate exercise in **Clean Architecture**,
**Domain-Driven Design**, and **Hexagonal (Ports & Adapters)** patterns, organized
as a **modular monolith** with feature-based slices. The library domain (books,
members, loans, plus authentication, email verification, and outbound notifications)
is a vehicle — the real subject is how to organize async Python code so that
business logic, persistence, transport, and infrastructure can evolve independently.

> 396 tests. Every architectural claim below is enforced by a test.

---

## Table of contents

- [The Dependency Rule, made concrete](#the-dependency-rule-made-concrete)
- [Project layout](#project-layout)
- [Core patterns demonstrated](#core-patterns-demonstrated)
- [Auth & email verification](#auth--email-verification)
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
`loan/`, `auth/`, `notification/`), and **layered hexagonally** inside each slice:

```
                  ┌─────────────────────────────────────────────────┐
                  │  presentation/  ── HTTP (FastAPI)               │
                  │     ↓                                           │
                  │  application/   ── use cases, commands,         │
                  │     ↓              app-level exceptions         │
                  │  domain/        ── entities, value objects,     │
                  │                    repository + service ports,  │
                  │                    domain exceptions            │
                  │     ↑                                           │
                  │  infrastructure/── SQL, Redis, SMTP, JWT,       │
                  │                    Argon2, in-memory adapters   │
                  └─────────────────────────────────────────────────┘
                applied inside book/, member/, loan/, auth/, notification/
```

**Source-code dependencies always point inward.** Within any slice,
[`<feature>/domain/`](library/book/domain/) imports nothing from `application/`,
`infrastructure/`, or `presentation/`. `application/` imports only from `domain/`.
`infrastructure/` implements `domain/` protocols. `presentation/` orchestrates
everything from the outside.

**Cross-slice imports are allowed where they are natural and one-way.**

- [`loan/`](library/loan/) imports `BookRepository`, `MemberRepository`, and a few
  exceptions from `book/` and `member/`, because borrowing a book genuinely spans
  three aggregates. `book/` and `member/` do not know about `loan/`.
- [`member/`](library/member/) imports the `Notifier` port + `Notification` value
  object from [`notification/`](library/notification/) to send the welcome email
  on registration.
- [`auth/`](library/auth/) defines a `CredentialVerifier` port; the implementation
  ([`MemberCredentialVerifier`](library/member/infrastructure/credential_verifier.py))
  lives in `member/infrastructure/`. Only the impl direction crosses the slice
  boundary — `auth.application` no longer imports from `member.domain` at all.
- [`member/`](library/member/) defines its own `VerificationTokenIssuer` port and
  impl, so the email-verification flow does not depend on `auth.TokenIssuer`.

[`shared/`](library/shared/) holds genuinely cross-cutting infrastructure
(`Clock` port, cache adapters, structured `Logger` port, shared SQL `MetaData`,
config, structlog setup) and the composition root (FastAPI app entry point + the
DI module that wires concrete adapters across slices).

This is enforced not by tooling but by discipline + tests. Try violating it and
contract tests start failing in unintuitive ways.

---

## Project layout

```
library/
├── book/                          # Bounded context: books
│   ├── domain/
│   │   ├── model.py               # Book (entity, with description)
│   │   ├── value_objects.py       # ISBN (immutable, validated)
│   │   ├── repository.py          # BookRepository  ← Protocol (port)
│   │   └── exceptions.py          # BookNotFound, BookNotAvailable
│   ├── application/
│   │   ├── commands.py            # AddBookCommand, UpdateBookCommand
│   │   ├── exceptions.py          # BookAlreadyExists
│   │   └── use_cases/             # One file per use case (SRP)
│   │       ├── add_book.py
│   │       ├── update_book.py
│   │       ├── read_book.py
│   │       ├── list_books.py
│   │       └── delete_book.py
│   ├── infrastructure/
│   │   ├── in_memory_repository.py
│   │   ├── sql_table.py           # books_table (uses shared MetaData)
│   │   ├── sql_repository.py
│   │   └── cached_repository.py   # CachedBookRepository (Decorator)
│   └── presentation/api/          # schemas, dependencies, router
│
├── member/                        # Bounded context: members (identity)
│   ├── domain/
│   │   ├── model.py               # Member (with is_verified + mark_verified)
│   │   ├── value_objects.py       # Email, Password
│   │   ├── repository.py
│   │   ├── services.py            # VerificationTokenIssuer (port)
│   │   └── exceptions.py          # MemberNotFound, InvalidVerificationToken
│   ├── application/
│   │   ├── exceptions.py          # MemberAlreadyExists, MemberNotVerified
│   │   └── use_cases/
│   │       ├── add_member.py      # registration: hash, persist, email link
│   │       ├── verify_member.py   # confirm email (idempotent)
│   │       ├── read_member.py
│   │       ├── list_members.py
│   │       └── delete_member.py
│   ├── infrastructure/
│   │   ├── in_memory_repository.py
│   │   ├── sql_table.py
│   │   ├── sql_repository.py
│   │   ├── cached_repository.py
│   │   ├── credential_verifier.py             # implements auth.CredentialVerifier
│   │   └── pyjwt_verification_token_issuer.py # implements VerificationTokenIssuer
│   └── presentation/api/
│
├── loan/                          # Bounded context: loans (multi-aggregate)
│   ├── domain/                    # Loan, LoanRepository, LoanNotFound
│   ├── application/               # BorrowBookUseCase, ReturnBookUseCase
│   ├── infrastructure/            # in-memory + SQL (no cache, no value objects)
│   └── presentation/api/          # router is gated by get_verified_member
│
├── auth/                          # Bounded context: authentication sessions
│   ├── domain/
│   │   ├── model.py               # RefreshToken
│   │   ├── repository.py          # RefreshTokenRepository
│   │   ├── services.py            # TokenIssuer, CredentialVerifier (ports)
│   │   └── exceptions.py          # InvalidAccessToken, RefreshToken{Invalid,
│   │                              #   Expired,Revoked,NotFound}
│   ├── application/
│   │   ├── token_pair.py          # TokenPair value object
│   │   ├── exceptions.py          # InvalidCredentials
│   │   └── use_cases/             # login, refresh, logout
│   ├── infrastructure/
│   │   ├── pyjwt_issuer.py        # PyJWTTokenIssuer (access + refresh only)
│   │   ├── in_memory_repository.py
│   │   ├── sql_table.py
│   │   └── sql_repository.py      # refresh tokens persisted hashed
│   └── presentation/api/
│       ├── router.py              # /auth/{login,refresh,logout}
│       ├── security.py            # get_current_member, get_verified_member
│       └── dependencies.py
│
├── notification/                  # Bounded context: outbound notifications
│   ├── domain/
│   │   ├── model.py               # Notification (subject + body + recipient)
│   │   └── services.py            # Notifier  ← Protocol (port)
│   └── infrastructure/
│       └── email_notifier.py      # EmailNotifier (aiosmtplib; log-only in dev)
│
└── shared/                        # Cross-cutting code
    ├── config.py                  # Pydantic Settings (fail-fast on missing env)
    ├── logging_config.py          # structlog + stdlib bridge
    ├── domain/exceptions.py       # DomainError (base)
    ├── application/
    │   ├── clock.py               # Clock (port)
    │   ├── password_hasher.py     # PasswordHasher (port)
    │   ├── logger.py              # Logger (port)
    │   └── exceptions.py          # ApplicationError (base)
    ├── infrastructure/
    │   ├── clock.py               # SystemClock
    │   ├── argon2_password_hasher.py  # Argon2PasswordHasher
    │   ├── structlog_logger.py    # get_logger (structlog bridge)
    │   ├── sql_metadata.py        # shared MetaData()
    │   └── cache/                 # Cache port + Redis / in-memory impls
    └── presentation/api/
        ├── main.py                # FastAPI app, lifespan, exception handlers
        ├── dependencies.py        # composition root for cross-slice DI
        └── middleware.py          # request_logging_middleware (structlog)

tests/                             # Mirrors the source tree 1:1
├── conftest.py                    # Cross-feature fixtures (valid_*, clock,
│                                  #   token_issuer, credential_verifier,
│                                  #   verification_token_issuer, client)
├── book/{domain, application, infrastructure, presentation/api/}
├── member/{…}
├── loan/{…}
├── auth/{…}
├── notification/{…}
└── shared/{infrastructure, test_config.py}
```

Browse the source: [`library/`](library/) · [`tests/`](tests/).

---

## Core patterns demonstrated

### Repository Pattern (Ports & Adapters)

[`BookRepository`](library/book/domain/repository.py),
[`MemberRepository`](library/member/domain/repository.py),
[`LoanRepository`](library/loan/domain/repository.py), and
[`RefreshTokenRepository`](library/auth/domain/repository.py) are
`typing.Protocol` classes living in each feature's `domain/`. Three or four
concrete implementations live in the feature's `infrastructure/`:
`InMemory*`, `Sql*`, plus a `Cached*` decorator (books and members only).
Use cases depend only on the protocol; they have no idea which backend they're
talking to.

A single contract test suite is parametrized over every implementation
([`tests/book/infrastructure/conftest.py`](tests/book/infrastructure/conftest.py)):

```python
@pytest.fixture(params=["in_memory", "sql", "cache_redis", "cache_in_memory"])
async def empty_book_repo(request, sql_book_repo):
    ...
```

If a new implementation passes the contract suite, it is provably substitutable
(LSP). Contract tests run across the four repos × multiple backends.

Repository `save` is split into explicit `create` (insert; raises on duplicate
id) and `update` (mutate existing; raises on missing) so accidental upserts
become loud failures rather than silent data shape drift.

### Two-port split for JWTs (Interface Segregation)

JWTs are used for two unrelated jobs in this codebase: short-lived **access
tokens** for authentication, and single-use **verification tokens** for email
confirmation. Two ports, two impls:

- [`auth.domain.TokenIssuer`](library/auth/domain/services.py): access tokens
  (issue + verify) and refresh tokens (generate + hash) — strictly authentication
  session concerns.
- [`member.domain.VerificationTokenIssuer`](library/member/domain/services.py):
  email verification tokens (issue + verify) — strictly an email-verification
  concern.

Each impl ([`PyJWTTokenIssuer`](library/auth/infrastructure/pyjwt_issuer.py),
[`PyJWTVerificationTokenIssuer`](library/member/infrastructure/pyjwt_verification_token_issuer.py))
uses the same `JWT_SECRET_KEY` but stamps a distinct `purpose` claim
(`access` vs `verify_email`) on its payload, so a token minted for one purpose
cannot be replayed against the other endpoint.

### Cross-slice port with member-side impl (`CredentialVerifier`)

[`auth.domain.CredentialVerifier`](library/auth/domain/services.py) is a port
that `LoginUseCase` consumes (`async verify(email, password) -> UUID`). Its
implementation, [`MemberCredentialVerifier`](library/member/infrastructure/credential_verifier.py),
lives in `member/infrastructure/` and internally uses `MemberRepository` +
`PasswordHasher` to do the actual lookup and verification.

The point: the auth slice's `LoginUseCase` does **not** import
`MemberRepository` or `Email` from `member.domain` — it only knows the port.
The member slice provides an adapter to that port, an asymmetric dependency
that keeps the auth slice slim while still letting login work against the
real member store.

### Notifier as a business port, not infrastructure

[`Notifier`](library/notification/domain/services.py) is a domain port that
sends a [`Notification`](library/notification/domain/model.py) value object —
**not** an "email service". The value object carries `recipient`, `subject`,
`body`; the channel is the impl's concern. Today the only impl is
[`EmailNotifier`](library/notification/infrastructure/email_notifier.py) via
`aiosmtplib`, but the use case
([`AddMemberUseCase`](library/member/application/use_cases/add_member.py))
doesn't know that — adding SMS or push later doesn't touch member code.

### Argon2 password hashing behind a port

[`PasswordHasher`](library/shared/application/password_hasher.py) is a port
in `shared.application`. Production uses
[`Argon2PasswordHasher`](library/shared/infrastructure/argon2_password_hasher.py)
(argon2-cffi, OWASP-recommended parameters); tests use a `FakePasswordHasher`
that produces deterministic, fast hashes (`"hashed:password"`). Switching cost
factors or algorithms is one constructor argument away — use cases never see it.

### Decorator Pattern (CachedBookRepository, CachedMemberRepository)

[`CachedBookRepository`](library/book/infrastructure/cached_repository.py) wraps
any `BookRepository` and adds Redis caching to `find_by_id`. The cache layer
itself is abstracted behind a `Cache` protocol
([`shared/infrastructure/cache/protocol.py`](library/shared/infrastructure/cache/protocol.py))
with two implementations:
[`RedisCache`](library/shared/infrastructure/cache/redis.py) (network) and
[`InMemoryCache`](library/shared/infrastructure/cache/in_memory.py) (LRU).
The decorator works against any cache, the cache works against any backend.
DIP applied recursively.

### Clock Pattern (testable time)

Use cases never call `datetime.now()` directly. They depend on a `Clock`
protocol ([`shared/application/clock.py`](library/shared/application/clock.py))
injected through the constructor. Production uses
[`SystemClock`](library/shared/infrastructure/clock.py); tests use a `FakeClock`
returning a fixed time. Tests can assert exact timestamps, not "within a few
seconds of now".

### Repository per Aggregate, ID references between aggregates

[`Loan`](library/loan/domain/model.py) references its book and member by `UUID`,
not by object reference. Each aggregate is loaded and saved independently. This
keeps consistency boundaries explicit and aggregates persistable in isolation —
and it is what makes the `loan/` slice possible without `book/` and `member/`
having to know about it.

### Configuration as code (fail-fast Pydantic Settings)

From [`library/shared/config.py`](library/shared/config.py):

```python
class Settings(BaseSettings):
    database_url: str                                          # required
    redis_url: str                                             # required
    jwt_secret_key: str = Field(min_length=32)                 # required, ≥32 bytes
    cache_ttl: int = Field(default=300, gt=0)
    log_level: LogLevel = "INFO"                               # Literal-typed
    log_format: LogFormat = "console"
    jwt_algorithm: JwtAlgorithm = "HS256"                      # Literal-typed
    access_token_ttl_minutes: int = Field(default=15, gt=0)
    refresh_token_ttl_days: int = Field(default=30, gt=0)
    verification_token_ttl_hours: int = Field(default=24, gt=0)
    app_base_url: str = "http://localhost:8000"
    smtp_host: str | None = None
    smtp_port: int = Field(default=587, gt=0)
    smtp_from: str = "library@example.com"
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_use_tls: bool = False

    model_config = SettingsConfigDict(env_file=".env", extra="forbid")
```

Required env vars are validated at import time, not on first use. URL fields
have prefix validators (`postgresql+asyncpg://`, `redis://`, …). Typos in env
names (`DATABSE_URL`) fail loudly thanks to `extra="forbid"`. `Literal` types
mean misspelled log levels or JWT algorithms refuse to boot.

### Structured logging with request context

`structlog` is configured in
[`library/shared/logging_config.py`](library/shared/logging_config.py) with
`contextvars.merge_contextvars`. The HTTP middleware
([`shared/presentation/api/middleware.py`](library/shared/presentation/api/middleware.py))
binds `request_id`, `method`, `path` once per request, and every downstream
log call — including SMTP failures three layers deep — automatically inherits
that context. Logs render as colorized console output in development, JSON in
production. Use cases depend on the `Logger` port
([`shared/application/logger.py`](library/shared/application/logger.py)), not
on `structlog` directly.

---

## Auth & email verification

The full lifecycle of a member:

```
POST /members                            # register
  → AddMemberUseCase
      • Argon2-hash password
      • member_repo.create(member, is_verified=False)
      • issue verification token (purpose=verify_email, 24h TTL)
      • Notifier.send: "open {app_base_url}/members/verify?token=…"
  ← 201 {id, name, email, is_verified=false}

POST /members/verify {token}             # confirm email (idempotent)
  → VerifyMemberUseCase
      • VerificationTokenIssuer.verify(token) → member_id
      • short-circuit if already verified (no SQL UPDATE)
      • else: member.mark_verified(); member_repo.update(member)
  ← 200 {id, name, email, is_verified=true}

POST /auth/login {email, password}       # exchange creds for tokens
  → LoginUseCase
      • CredentialVerifier.verify(email, password) → member_id
        (impl lives in member/, raises InvalidCredentials on any failure)
      • issue access JWT (15m, purpose=access)
      • generate opaque refresh token, persist its SHA-256 hash
  ← 200 {access_token, refresh_token, token_type: "bearer"}

POST /loans {book_id, member_id}         # borrow — requires Bearer + verified
  → get_verified_member  (composed: get_current_member + is_verified check)
      • 401 if no/invalid token
      • 403 (MemberNotVerified) if verified=false
  → BorrowBookUseCase

POST /auth/refresh {refresh_token}       # rotate (single-use)
  → RefreshTokensUseCase
      • look up by SHA-256 hash; reject if invalid/expired/revoked
      • mark old token revoked, issue new pair
  ← 200 {access_token, refresh_token}

POST /auth/logout {refresh_token}        # revoke
  ← 204
```

Key properties:

- **Refresh-token rotation is single-use.** A replay of a previously rotated
  token returns 401, enforced by `RefreshTokenRevoked` — a basic mitigation
  against stolen-token replay.
- **Email verification gates `/loans/*`, not `/members`.** New members can be
  created and read regardless of `is_verified`; only the borrow/return actions
  require confirmation. The gate is a dependency
  ([`get_verified_member`](library/auth/presentation/api/security.py)) so any
  future endpoint can adopt it by one import.
- **Verification tokens carry `purpose=verify_email`.** Access tokens are
  rejected by `/members/verify` and vice versa, even though both are signed
  with the same `JWT_SECRET_KEY`.
- **The verification email contains a URL, not a raw token.** The link points
  at `{APP_BASE_URL}/members/verify?token=…`; a frontend (or curl) is expected
  to consume it and POST the token to the verify endpoint.

---

## Test pyramid

| Layer | Tests | What it proves |
|-------|------:|----------------|
| Domain (book + member + loan + auth + notification) | ~90 | Business rules and value-object invariants without any I/O |
| Application (use cases) | ~70 | Orchestration logic with in-memory fakes — including login, refresh rotation, verification, registration with welcome email |
| Infrastructure contract (repositories) | ~120 | Every repository implementation satisfies its protocol (LSP) across 4 backends (in-memory, SQL, Redis-cached, in-memory-cached) |
| JWT issuer impls | ~15 | Access tokens decode, expire, reject tampering; verification tokens reject access tokens and vice versa (`purpose` claim) |
| Cache behavior | ~12 | Decorators cache on read, invalidate on write (book + member) |
| In-memory cache | 11 | LRU eviction, move-to-end on access |
| Clock + Logger + PasswordHasher | ~10 | Each port has a real impl that satisfies the protocol |
| Config fail-fast | ~25 | Every required field, type literal, and validator is exercised — bad input refuses to boot |
| API end-to-end | ~45 | HTTP ↔ use case translation, exception → status mapping, auth and verification flows |

**Total: 396 tests.** Each level tests one rung of abstraction; almost no
duplication between levels. Run with `pytest -W error` — warnings are
treated as failures.

---

## Tech stack

- **Python 3.12+** (async/await throughout)
- **FastAPI** — driving HTTP adapter
- **SQLAlchemy 2.x Core** (not ORM) — dialect-agnostic SQL
- **asyncpg** / **aiosqlite** — async database drivers
- **redis-py** (async) — cache adapter
- **PyJWT** — JWT encoding/decoding for access and verification tokens
- **argon2-cffi** — password hashing (OWASP-recommended Argon2id)
- **aiosmtplib** — async SMTP for the email notifier
- **pydantic + pydantic-settings** — schemas and fail-fast configuration
- **structlog** — structured, context-aware logging
- **pytest + pytest-asyncio** — test runner (`-W error` clean)
- **httpx + ASGITransport** — in-process HTTP testing
- **fakeredis** — in-process Redis for cache tests
- **pylint** — 10.00/10 on the project tree

Pinned versions live in [`pyproject.toml`](pyproject.toml).

---

## Getting started

### Prerequisites

- Python 3.12+
- (Optional, for full local run) PostgreSQL and Redis
- (Optional, for real email delivery) an SMTP relay — without one, the
  `EmailNotifier` logs the email instead of sending it.

### Install

```sh
python -m venv .venv
.venv\Scripts\activate           # Windows
# source .venv/bin/activate      # macOS / Linux

pip install -e ".[dev]"
```

### Configure

Copy [`.env.example`](.env.example) to `.env` and fill in real values. The
required fields are `DATABASE_URL`, `REDIS_URL`, and `JWT_SECRET_KEY` (must
be at least 32 bytes for HS256):

```sh
# --- required ---
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/library
REDIS_URL=redis://localhost:6379/0
JWT_SECRET_KEY=replace-me-with-at-least-32-bytes-of-random-secret

# --- optional, with sensible defaults ---
CACHE_TTL=300
LOG_LEVEL=INFO
LOG_FORMAT=console
JWT_ALGORITHM=HS256
ACCESS_TOKEN_TTL_MINUTES=15
REFRESH_TOKEN_TTL_DAYS=30
VERIFICATION_TOKEN_TTL_HOURS=24
APP_BASE_URL=http://localhost:8000

# --- email (optional; without SMTP_HOST, the email is logged not sent) ---
SMTP_HOST=
SMTP_PORT=587
SMTP_FROM=library@example.com
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_USE_TLS=false
```

For quick local experimentation without Postgres, you can point at a file:

```sh
DATABASE_URL=sqlite+aiosqlite:///./library.db
```

Generate a strong JWT secret:

```sh
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

### Run tests

```sh
pytest                # 396 tests, warnings-as-errors
pylint library tests  # 10.00/10
```

### Run the API

```sh
uvicorn library.shared.presentation.api.main:app --reload
```

Then open `http://localhost:8000/docs` for the interactive Swagger UI.

---

## HTTP API

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| `GET` | `/books` | — | List all books |
| `POST` | `/books` | — | Add a book (201 / 409 / 422) |
| `GET` | `/books/{id}` | — | Read a book (200 / 404) |
| `PUT` | `/books/{id}` | — | Update a book (200 / 404 / 422) |
| `DELETE` | `/books/{id}` | — | Delete a book (204 / 404) |
| `GET` | `/members` | — | List all members |
| `POST` | `/members` | — | Register a member (201 / 409 / 422); sends verification email |
| `POST` | `/members/verify` | — (token in body) | Confirm email (200 / 401 / 404 / 422) |
| `GET` | `/members/{id}` | — | Read a member (200 / 404) |
| `DELETE` | `/members/{id}` | — | Delete a member (204 / 404) |
| `POST` | `/auth/login` | — | Exchange credentials for tokens (200 / 401 / 422) |
| `POST` | `/auth/refresh` | — | Rotate token pair (200 / 401) |
| `POST` | `/auth/logout` | — | Revoke refresh token (204) |
| `POST` | `/loans` | **Bearer + verified** | Borrow a book (201 / 401 / 403 / 404 / 409) |
| `POST` | `/loans/{id}/return` | **Bearer + verified** | Return a book (200 / 401 / 403 / 404) |
| `GET` | `/health` | — | Liveness probe |

Exceptions are mapped to HTTP statuses centrally in
[`shared/presentation/api/main.py`](library/shared/presentation/api/main.py):

```python
BookNotFound, MemberNotFound, LoanNotFound       → 404
BookAlreadyExists, MemberAlreadyExists           → 409
BookNotAvailable                                 → 409
InvalidCredentials                               → 401
InvalidAccessToken                               → 401
RefreshTokenInvalid / Expired / Revoked / NotFound → 401
InvalidVerificationToken                         → 401
MemberNotVerified                                → 403
ValueError                                       → 422  # invalid VO / domain invariant
```

Routers (one per slice, under
[`<feature>/presentation/api/router.py`](library/book/presentation/api/router.py))
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
- **Non-root user** — the process runs as user `app`, not as root.
- **`python:3.12-slim`** base — small (~50 MB) and glibc-based, compatible
  with `asyncpg`, `argon2-cffi`, and other binary wheels that Alpine sometimes
  breaks.
- **Healthcheck** — Docker hits `/health` every 30 s.
- **`PYTHONUNBUFFERED=1`** — logs go straight to stdout (essential for
  structlog's JSON output).

### Build

```sh
docker build -t library:latest .
```

### Run

The image expects `DATABASE_URL`, `REDIS_URL`, and `JWT_SECRET_KEY` from the
environment — there is no `.env` baked into the image (that would be a
secret-leakage anti-pattern).

```sh
docker run --rm -p 8000:8000 \
    -e DATABASE_URL="sqlite+aiosqlite:///./library.db" \
    -e REDIS_URL="redis://host.docker.internal:6379/0" \
    -e JWT_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')" \
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
  baked into site-packages.
- **`depends_on: condition: service_healthy`** — the app waits for
  Postgres `pg_isready` and Redis `PING` before starting.
- **Persistent Postgres data** — a named volume `postgres_data` keeps
  the database between `compose down` / `compose up`. To wipe it:
  `docker compose down -v`.
- **`LOG_FORMAT=console`, `LOG_LEVEL=DEBUG`** — overrides for
  human-readable, verbose dev logs.

---

## Architectural decisions worth highlighting

### Hybrid: hexagonal layers inside feature folders

A classic hexagonal codebase groups by *technical layer* — one `domain/`, one
`application/`, one `infrastructure/`, one `api/`. That answers "what kind of
code is this?" but forces a developer working on "books" to touch five or six
folders.

A pure Vertical-Slice Architecture goes the other way and slices per use case —
`book/add_book/`, `book/read_book/`, etc. — but at this project's size that
produces many almost-empty per-slice `domain/` and `infrastructure/` folders
that just re-export shared types.

This codebase picks the **middle**: slice by bounded context (`book/`, `member/`,
`loan/`, `auth/`, `notification/`), keep hexagonal layers inside each slice.
You get the "everything about books is in one place" win, you keep hexagonal
discipline, and the layer folders inside a slice are actually populated. Going
further to per-use-case slices is left as a path you take when individual use
cases start having genuinely independent schemas, persistence concerns, or
owners — not before.

### Identity lives in `member/`, sessions live in `auth/`

The `Member` aggregate owns the things that define a person who can use the
library (`name`, `email`, `password_hash`, `is_verified`). Creating, reading,
updating, deleting, and verifying members all live in `member.application` —
the slice that owns the aggregate owns its lifecycle.

`auth/` owns **session mechanics**: issuing access tokens, generating and
rotating refresh tokens, revoking on logout. It does not own user identity;
it consumes it via the `CredentialVerifier` port. If "register" feels like an
auth concern in your head, that's a UI convention (Django, Devise, NextAuth) —
not an architectural truth.

### Cross-slice ports go in the consumer; impls live with the data

[`CredentialVerifier`](library/auth/domain/services.py) is the canonical
example. The port is defined in `auth.domain` because the auth slice is the
consumer (LoginUseCase needs it). The impl
([`MemberCredentialVerifier`](library/member/infrastructure/credential_verifier.py))
lives in `member.infrastructure` because that's where the data — the
`MemberRepository` — actually is. Composition root in
[`shared/presentation/api/dependencies.py`](library/shared/presentation/api/dependencies.py)
wires them together at process boundary.

This keeps the consumer slim (`auth.application` imports nothing from
`member.domain`) while still letting the consumer talk to the data through a
well-defined contract.

### `shared/` for cross-cutting code, not a junk drawer

[`shared/`](library/shared/) holds only code that is **provably cross-cutting**:
the `Clock` port (every use case that needs time), the `PasswordHasher` port
(registration + login), the `Logger` port (everywhere), the `Cache` protocol
(used by multiple features' cached repositories), shared SQL `MetaData` (so all
tables register into one schema), the FastAPI composition root, config, and
logging. Domain models, repositories, and use cases all live in their feature
folder. The rule is: if exactly one feature uses it, it belongs in that feature.

The composition root in `shared/presentation/api/dependencies.py` is the **one
place** that imports concrete implementations from every slice and wires them
together — that's where cross-slice DI is allowed, not in the slices themselves.

### Repository protocols live in `<feature>/domain/`, not `<feature>/application/`

The repository expresses what the domain **demands** from persistence, in
domain language (`find_by_isbn`, not `SELECT * FROM books`). It is the domain's
outward-facing port. Implementations belong outside the domain; the interface
belongs inside it. See
[`book/domain/repository.py`](library/book/domain/repository.py).

### `Cache` protocol lives in `shared/infrastructure/`, not in any domain

Caching is a runtime optimization — domain entities know nothing about it. The
protocol
([`shared/infrastructure/cache/protocol.py`](library/shared/infrastructure/cache/protocol.py))
is consumed only by other infrastructure code (`CachedBookRepository`,
`CachedMemberRepository`). It is an *internal* abstraction of the infrastructure
layer, not a domain concern.

### Pydantic schemas in `<feature>/presentation/api/`, never in `<feature>/domain/`

[`BookCreate` and `BookResponse`](library/book/presentation/api/schemas.py) are
HTTP DTOs. They translate between HTTP and domain. Validation of HTTP-format
concerns (required fields, JSON types) happens in the schema; validation of
domain invariants (non-empty title, valid ISBN format, password length) happens
in the [entity](library/book/domain/model.py). No duplication — the API schema
is intentionally permissive, the domain rejects invalid state.

### Session-per-request, not Unit of Work

A `UnitOfWork` abstraction was introduced and then removed. For this project,
FastAPI's per-request dependency cache plus `get_session` in
[`shared/presentation/api/dependencies.py`](library/shared/presentation/api/dependencies.py)
(which commits on success, rolls back on exception) already provide transactional
consistency across multiple repositories — the same session is shared
automatically. A separate `UnitOfWork` layer would have duplicated this without
adding value.

The lesson: **a pattern earns its place by solving present pain, not by
appearing in textbooks.**

### Use cases are classes, not functions

`AddBookUseCase`, `BorrowBookUseCase`, `LoginUseCase`, `VerifyMemberUseCase`,
etc. each have a single `execute(command)` method. Constructor injection of
dependencies, one file per use case (easy to find, hard to merge-conflict),
stable surface even when the algorithm changes, natural map to the Command
pattern.

### CRUD use cases get individual repositories; multi-aggregate use cases too

The simple use cases ([`AddBookUseCase`](library/book/application/use_cases/add_book.py),
[`DeleteBookUseCase`](library/book/application/use_cases/delete_book.py)) take
one repository. [`BorrowBookUseCase`](library/loan/application/use_cases/borrow_book.py)
takes three (`books`, `members`, `loans`) plus a `Clock`. FastAPI's DI cache
ensures they share the same SQL session within a request, so atomicity is
preserved without extra abstractions.

### Application exceptions vs domain exceptions — and when they cross slices

Domain exceptions (`MemberNotFound`, `InvalidVerificationToken`,
`BookNotAvailable`) live in `<feature>/domain/exceptions.py` — they express
broken invariants. Application exceptions (`MemberAlreadyExists`,
`MemberNotVerified`, `InvalidCredentials`) live in
`<feature>/application/exceptions.py` — they express policy violations enforced
by use cases or HTTP gates. Both base classes (`DomainError`,
`ApplicationError`) live in `shared/`, and the HTTP layer maps subclasses to
status codes generically.

`MemberNotVerified` is the policy example: it's an `ApplicationError` (not a
domain exception) because "you must be verified to borrow" is a workflow rule
enforced by the loan endpoint, not an invariant of the `Member` aggregate
itself — an unverified Member is a perfectly valid Member, just one that can't
yet borrow.

---

## What this project deliberately does **not** do

These were considered and intentionally left out:

- **Per-use-case slicing** — see the architecture decision above. Per-entity
  slices hit the cost/benefit sweet spot at this size.
- **CQRS** — read and write models are the same. No projection layer.
- **Event sourcing** — state is the current value of fields, not a log of
  events.
- **Domain event bus** — `AddMemberUseCase` calls `Notifier.send` directly
  rather than publishing a `MemberRegistered` event. With exactly one
  subscriber (the welcome email), an event bus would be ceremony without
  decoupling. The trigger to extract is "second subscriber" — then it earns
  the abstraction.
- **Authorization roles / RBAC** — there is authentication (who are you) and
  one verified-email gate, but no concept of admin vs. member roles. Adding
  it would be a new dependency composed on top of `get_current_member` in the
  same shape as `get_verified_member`.
- **Pagination / filtering on list endpoints** — outside the demonstration
  scope.
- **Generic `BaseEntity`** — premature abstraction. Each entity defines its
  own `__eq__` / `__hash__` by `id`.
- **Unit of Work** — see above. Removed after measuring that
  session-per-request carried the same weight.
- **Token blocklist on access tokens** — access tokens are short-lived (15
  minutes) and stateless, so revocation is implicit. Refresh tokens, which
  live for 30 days, are tracked server-side and can be revoked.

---

## License

MIT.
