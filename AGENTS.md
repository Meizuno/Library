# AGENTS.md

Mandatory rules for AI agents working in this repository. These rules are enforced by 396 tests and `pylint library tests` (10.00/10). Violations break the build.

For setup, motivation, and detailed architecture rationale, see [README.md](README.md).

---

## Project at a glance

Python 3.12+ async backend, FastAPI driver, SQLAlchemy 2.x Core, Postgres + Redis. Built as a **modular monolith** sliced by **bounded context** (`book/`, `member/`, `loan/`, `auth/`, `notification/`), with **hexagonal layers inside each slice**:

```
presentation/  ── HTTP (FastAPI)
   ↓
application/   ── use cases, commands, app-level exceptions
   ↓
domain/        ── entities, value objects, repository + service ports, domain exceptions
   ↑
infrastructure/── SQL, Redis, SMTP, JWT, Argon2, in-memory adapters
```

`shared/` holds genuinely cross-cutting code (Clock port, PasswordHasher port, Logger port, Cache protocol, config, structlog setup, FastAPI composition root).

---

## The Dependency Rule (non-negotiable)

**Source-code dependencies always point inward.**

Inside a slice:
- `domain/` imports **nothing** from `application/`, `infrastructure/`, or `presentation/`
- `application/` imports **only** from `domain/`
- `infrastructure/` implements `domain/` protocols (`typing.Protocol`)
- `presentation/` orchestrates from the outside

Cross-slice imports are **one-way and explicit**:
- `loan/` may import `BookRepository`, `MemberRepository`, and exceptions from `book/`, `member/`
- `member/` uses `Notifier` port + `Notification` from `notification/`
- `auth/` defines `CredentialVerifier` port; impl `MemberCredentialVerifier` lives in `member/infrastructure/`
- `book/` and `member/` know **nothing** about `loan/`

**Hard forbidden:**
- ❌ Importing `infrastructure` from `domain` or `application`
- ❌ Putting SQL strings, Pydantic schemas, or HTTP types in `domain/`
- ❌ Returning ORM rows from repository — map to domain Entity in infrastructure
- ❌ Use cases calling `datetime.now()`, `random.random()`, `logger.info()` directly — use `Clock`, `Random`, `Logger` ports
- ❌ Mutating module-level state
- ❌ `try/except` in routers — let exceptions bubble to centralized handlers

---

## Mandatory patterns

### Repository Pattern (Ports & Adapters)

- Protocol in `<feature>/domain/repository.py`
- Implementations in `<feature>/infrastructure/`: `InMemory*`, `Sql*`, optional `Cached*` decorator
- **`create(entity)` vs `update(entity)` are separate** — no upserts. `create` raises on duplicate id; `update` raises on missing.
- Methods use **domain language** (`find_by_isbn`), not SQL primitives
- All implementations must pass the parametrized contract test in `tests/<feature>/infrastructure/conftest.py`

### Use Cases as classes

- One file per use case under `<feature>/application/use_cases/<verb>_<noun>.py`
- Class name = `<Verb><Noun>UseCase` (e.g., `AddBookUseCase`, `BorrowBookUseCase`)
- Single `async execute(command)` method
- Constructor injection of all dependencies (no `Depends()` inside the class)
- Use case **commands** (input DTOs) live in `<feature>/application/commands.py` as frozen dataclasses

### Value Objects

- `@dataclass(frozen=True)`
- Validation in `__post_init__`
- Use `object.__setattr__` for normalization (frozen workaround)
- Examples: [`ISBN`](library/book/domain/value_objects.py), [`Email`](library/member/domain/value_objects.py), [`Password`](library/member/domain/value_objects.py)

### Entities

- `@dataclass(kw_only=True)` (not frozen — entities have lifecycle)
- `id: UUID = field(init=False, default_factory=uuid4)`
- `__eq__` and `__hash__` **by id**
- Validation in `__post_init__`

### Clock port (testable time)

- Use cases never call `datetime.now()`
- Inject [`Clock`](library/shared/application/clock.py) protocol
- Production: `SystemClock`. Tests: `FakeClock(fixed_time)`

### Logger port

- Use cases never `import structlog`
- Inject [`Logger`](library/shared/application/logger.py) protocol
- Production: structlog-backed via [`get_logger`](library/shared/infrastructure/structlog_logger.py)
- Request context (`request_id`, `method`, `path`) is auto-bound via `contextvars.merge_contextvars`

### PasswordHasher port

- [`PasswordHasher`](library/shared/application/password_hasher.py) in `shared.application`
- Production: `Argon2PasswordHasher` (argon2-cffi, OWASP defaults)
- Tests: `FakePasswordHasher` producing deterministic `"hashed:<password>"`

### Two JWT ports (ISP)

- `auth.domain.TokenIssuer` — access + refresh tokens (purpose=`access`)
- `member.domain.VerificationTokenIssuer` — email-verification tokens (purpose=`verify_email`)
- Same `JWT_SECRET_KEY`, distinct `purpose` claim — tokens for one purpose are rejected by endpoints for another

### Notifier as business port

- [`Notifier`](library/notification/domain/services.py) sends a [`Notification`](library/notification/domain/model.py) VO (`recipient`, `subject`, `body`) — **not** an "email service"
- Channel (email / SMS / push) is the impl's concern
- Use case never knows what channel is used

### Decorator pattern for caching

- `CachedBookRepository` / `CachedMemberRepository` wrap any repository
- Cache layer abstracted behind [`Cache`](library/shared/infrastructure/cache/protocol.py) protocol with `RedisCache` and `InMemoryCache` impls
- Cache **invalidates on writes**, populates on `find_by_id`

### Pydantic Settings — fail-fast

- All config in [`Settings`](library/shared/config.py) with `extra="forbid"`
- `Literal`-typed enums for `LOG_LEVEL`, `LOG_FORMAT`, `JWT_ALGORITHM`
- `Field(min_length=...)` / `Field(gt=0)` validators
- URL fields have prefix validators

---

## Exception taxonomy

Two base classes in `shared/`:
- `DomainError` — broken invariants
- `ApplicationError` — workflow / policy violations

| Layer | Path | Examples |
|---|---|---|
| Domain | `<feature>/domain/exceptions.py` | `BookNotFound`, `BookNotAvailable`, `MemberNotFound`, `InvalidVerificationToken`, `LoanNotFound`, `RefreshTokenInvalid` |
| Application | `<feature>/application/exceptions.py` | `BookAlreadyExists`, `MemberAlreadyExists`, `MemberNotVerified`, `InvalidCredentials` |

**Centralized HTTP mapping** in [`shared/presentation/api/main.py`](library/shared/presentation/api/main.py):

```
BookNotFound, MemberNotFound, LoanNotFound       → 404
BookAlreadyExists, MemberAlreadyExists           → 409
BookNotAvailable                                  → 409
InvalidCredentials, InvalidAccessToken           → 401
RefreshTokenInvalid/Expired/Revoked/NotFound     → 401
InvalidVerificationToken                          → 401
MemberNotVerified                                 → 403
ValueError                                        → 422
```

**Routers never `try/except`.** They let exceptions bubble.

---

## File organization rules

- **One file per use case** in `<feature>/application/use_cases/`
- **Pydantic API schemas** in `<feature>/presentation/api/schemas.py` — never in `domain/`
- **SQL tables** in `<feature>/infrastructure/sql_table.py`, registered to the shared `MetaData()` from [`shared/infrastructure/sql_metadata.py`](library/shared/infrastructure/sql_metadata.py)
- **Repository protocols** in `<feature>/domain/repository.py`, **never** in `application/`
- **Composition root** is `shared/presentation/api/dependencies.py` — the **only** place that imports concretes across slices

---

## Tests

396 tests total. Test tree mirrors source tree 1:1.

- **Test runner:** `pytest -W error` (warnings = failures)
- **Asyncio mode:** `auto` (from `pyproject.toml`)
- **Contract tests** are parametrized over every repository impl (`in_memory`, `sql`, `cache_redis`, `cache_in_memory`)
- **Cross-feature fixtures** in [`tests/conftest.py`](tests/conftest.py): `valid_*`, `clock`, `token_issuer`, `credential_verifier`, `verification_token_issuer`, `client`
- **No real I/O in unit tests** — use in-memory repos, FakeClock, fakeredis, FakePasswordHasher

---

## Commands

| Task | Command |
|---|---|
| Install | `pip install -e ".[dev]"` |
| Run tests (warnings-as-errors) | `pytest -W error` |
| Lint (must score 10.00/10) | `pylint library tests` |
| Spell-check | `codespell --skip="*.lock,.git,__pycache__,.venv,*.egg-info"` |
| Security: code | `bandit -r library` |
| Security: deps | `pip-audit --skip-editable` |
| Security: licenses | `pip-licenses --fail-on="GPL;LGPL;AGPL"` |
| Run API locally | `uvicorn library.shared.presentation.api.main:app --reload` |
| Docker dev stack | `docker compose up --build` |

CI runs all of the above on every push / PR. See [.github/workflows/ci.yml](.github/workflows/ci.yml).

---

## TypeScript-style standards (Python edition)

- **Python 3.12+** — required `match`-statements, `PEP 695` generics permitted
- **Async everywhere** — repositories, use cases, services. Sync handlers are an anti-pattern
- **Type hints mandatory** on all public functions, methods, class attributes
- **Avoid `Any`** — use `object`, `unknown` workarounds, or precise unions
- **Avoid `# type: ignore`** — fix the type instead
- **No `eslint-disable` equivalents** (`# pylint: disable=...`) without a justifying comment
- **Prefer named types** over deep inline unions for repeated structures

---

## Verification checklist before completing a task

Before considering work done, AI agents must verify:

1. ✅ **No layer violations** — `domain/` doesn't import infrastructure; `application/` doesn't import infrastructure
2. ✅ **No ORM leakage** — repositories return domain entities, not SQL rows
3. ✅ **`pytest -W error`** runs clean (all 396 tests + zero warnings)
4. ✅ **`pylint library tests`** scores 10.00/10
5. ✅ **No `datetime.now()`** outside the `Clock` impl in `shared/infrastructure/clock.py`
6. ✅ **No `try/except`** in routers
7. ✅ **New use cases** are classes with single `execute(command)`, in `<feature>/application/use_cases/<verb>_<noun>.py`
8. ✅ **New repositories** pass the parametrized contract test
9. ✅ **HTTP responses** use Pydantic schemas from `<feature>/presentation/api/schemas.py`, not raw dicts or domain entities

---

## What this project deliberately does NOT do

If an agent is tempted to add any of the following, **stop and confirm with the human first**:

- ❌ **Domain Event Bus** — direct calls (`Notifier.send`) are correct until there are two subscribers
- ❌ **CQRS / Event Sourcing** — read/write models are the same; no event log
- ❌ **Generic `BaseEntity`** — each entity defines its own `__eq__` / `__hash__`
- ❌ **Unit of Work** — session-per-request via FastAPI DI already carries transactional consistency; UoW was added and removed
- ❌ **RBAC / role system** — authentication exists, authorization is one `is_verified` gate, no roles
- ❌ **Per-use-case slicing** — slices are per bounded context, not per use case
- ❌ **Pagination / filtering on list endpoints** — out of scope
- ❌ **Token blocklist on access tokens** — they're 15-min stateless; only refresh tokens are revocable

**The lesson behind these choices:** a pattern earns its place by solving present pain, not by appearing in textbooks.

---

## When in doubt

1. Re-read the README — every architectural claim there is enforced by a test
2. Read tests in the same area as your change — they describe expected behavior
3. Run `pytest -W error && pylint library tests` before considering work done
4. If you want to introduce a pattern not used elsewhere in the codebase, **ask first**
