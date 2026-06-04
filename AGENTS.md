# AGENTS.md

Mandatory rules for AI agents working in this repository. These rules are enforced by 402 tests, `ruff check library tests` (clean), and `mypy library tests` (clean). Violations break the build.

For setup, motivation, and detailed architecture rationale, see [README.md](README.md).

---

## Project at a glance

Python 3.12+ async backend, FastAPI driver, SQLAlchemy 2.x Core, Postgres + Redis. Built as a **modular monolith** with one bounded context (the library), sliced into **modules** (`book/`, `member/`, `loan/`, `auth/`, `notification/`). Each module is **flat** — no `domain/` / `application/` / `infrastructure/` / `presentation/` subfolders inside. The dependency rule is encoded by file, not by directory.

```
<module>/
├── models.py        ── entities + value objects (framework-free)
├── ports.py         ── all Protocols owned by this module (framework-free)
├── exceptions.py    ── domain + application exceptions (DomainError / ApplicationError split)
├── repositories.py  ── all port impls + the module's SQLAlchemy Table definition
├── use_cases/       ── one file per use case; Command DTO + UseCase class together
└── api/             ── FastAPI router(s), DI providers, request/response schemas
```

[`shared/`](library/shared/) holds genuinely cross-cutting code (Clock port, PasswordHasher port, Logger port, Cache protocol, the FastAPI app + composition root, config, structlog setup). It has its own flat layout: `ports.py`, `exceptions.py`, `adapters.py` (all impls), `config.py`, `logging_config.py`, `api/` (main app + composition root + middleware).

---

## The Dependency Rule (non-negotiable)

**Source-code dependencies always point inward.**

Inside a module:
- `models.py` imports **nothing** else from the module (only stdlib/typing).
- `ports.py` imports **only** `models.py`.
- `exceptions.py` imports only `library.shared.exceptions`.
- `repositories.py` imports `ports.py` + `models.py` + `exceptions.py` (+ `shared.adapters` for `metadata`, `shared.ports.Cache`, etc.). Only the composition root imports FROM `repositories.py`.
- `use_cases/*.py` import `ports.py`, `models.py`, `exceptions.py` (+ shared ports). They **never** import `repositories.py` or `api/`.
- `api/*` orchestrates: imports use cases + its own schemas. `api/` is the only place that knows about HTTP.

The domain (`models.py`, `ports.py`) stays **framework-free**: no Pydantic, no SQLAlchemy, no FastAPI imports.

Cross-module imports are **one-way and explicit**:
- `loan/` imports `BookRepository` + book exceptions from `book/`, and `MemberRepository` + member exceptions from `member/`.
- `member/use_cases/add_member.py` uses `Notifier` + `Notification` from `notification/`.
- `auth/ports.py` defines `CredentialVerifier`; the impl `MemberCredentialVerifier` lives in `member/repositories.py` (asymmetric — port in consumer, impl with the data).
- `book/` and `member/` know **nothing** about `loan/`.
- The composition root in [`library/shared/api/dependencies.py`](library/shared/api/dependencies.py) is the **only** place that imports concretes across modules. It bridges `auth.ports.CredentialVerifier` → `member.repositories.MemberCredentialVerifier` and `book.ports.BookAvailability` → `loan.repositories.LoanBookAvailability`.

**Hard forbidden:**
- ❌ Importing `repositories.py` from `models.py`, `ports.py`, or `use_cases/`
- ❌ Putting SQL strings, Pydantic schemas, or HTTP types in `models.py` or `ports.py`
- ❌ Returning ORM rows from repository methods — map to a domain entity inside `repositories.py`
- ❌ Use cases calling `datetime.now()`, `random.random()`, `logger.info()` directly — use `Clock`, `Random`, `Logger` ports
- ❌ Mutating module-level state
- ❌ `try/except` in routes — let exceptions bubble to centralized handlers in `shared/api/main.py`

---

## Mandatory patterns

### Repository Pattern (Ports & Adapters)

- Protocol in `<module>/ports.py`
- Implementations in `<module>/repositories.py`: `Sql<Entity>Repository` always; optional `Cached<Entity>Repository` decorator (book + member have it; loan + auth do not)
- **`create(entity)` vs `update(entity)` are separate** — no upserts. `create` raises on duplicate id; `update` raises on missing.
- Methods use **domain language** (`find_by_isbn`), not SQL primitives
- Every impl carries a `test_satisfies_X_protocol` test in `tests/<module>/repositories/test_contract.py` and the same parametrized contract test runs across all impls

### Soft delete (book, member)

- `books` and `members` tables carry `deleted_at: DateTime | None` — NULL = active row
- `SqlBookRepository.delete()` and `SqlMemberRepository.delete()` are `UPDATE ... SET deleted_at = NOW()`, not `DELETE FROM ...`
- Every read (`find_by_id`, `find_by_isbn` / `find_by_email`, `list_all`, `update`) filters `WHERE deleted_at IS NULL`
- The repository **observable contract is unchanged** — after `delete(id)`, `find_by_id(id)` returns None, `list_all()` excludes the row. The "soft" part is an SQL-impl detail.
- SQL-impl-specific guarantees (row physically stays, `deleted_at` is stamped, double-delete raises) are covered separately in [`tests/book/repositories/test_soft_delete.py`](tests/book/repositories/test_soft_delete.py) and [`tests/member/repositories/test_soft_delete.py`](tests/member/repositories/test_soft_delete.py)

### Foreign keys with `ondelete="RESTRICT"`

- `loans.book_id`, `loans.member_id`, and `refresh_tokens.member_id` reference parent tables with `ForeignKey(..., ondelete="RESTRICT")`
- In normal app flow nothing ever fires the constraint — books and members are soft-deleted, the parent rows stay physically present
- The FK is the safety net for any path that bypasses soft-delete: raw SQL, future GDPR-style hard-delete use cases, migrations
- New tables with cross-aggregate references must follow this pattern

### Detecting "0 rows affected" on UPDATE / DELETE

- Use `.returning(table.c.id)` on the statement and check `result.scalar_one_or_none() is None`
- Do **not** use `result.rowcount` — its only type on SQLAlchemy's `Result[Any]` requires `# type: ignore`. `RETURNING` works on Postgres and SQLite ≥ 3.35
- `scalar_one_or_none` also raises `MultipleResultsFound` if the primary-key WHERE ever matched more than one row, which is the right loud-on-violation behavior

### Repository search filters

- `BookRepository.list_all(search: str | None = None)` — optional case-insensitive substring filter matching against title **OR** author
- `None`, empty, and whitespace-only search mean "no filter — return everything"
- SQL impl uses `column.icontains(value, autoescape=True)` so user-supplied `%` / `_` cannot leak through as LIKE wildcards
- Soft-deleted rows remain excluded — the `deleted_at IS NULL` filter ANDs with the search filter

### Use Cases as classes

- One file per use case under `<module>/use_cases/<verb>_<noun>.py`
- Each file contains BOTH the `<Verb><Noun>Command` dataclass AND the `<Verb><Noun>UseCase` class
- Single `async execute(command)` method
- Constructor injection of all dependencies (no `Depends()` inside the class)

### Value Objects

- `@dataclass(frozen=True)`
- Validation in `__post_init__`
- Use `object.__setattr__` for normalization (frozen workaround)
- Examples: [`ISBN`](library/book/models.py), [`Email`, `Password`](library/member/models.py)

### Entities

- `@dataclass(kw_only=True)` (not frozen — entities have lifecycle)
- `id: UUID = field(init=False, default_factory=uuid4)`
- `__eq__(self, other: object) -> bool` and `__hash__(self) -> int` **by id**
- Validation in `__post_init__`

### Clock port (testable time)

- Use cases never call `datetime.now()`
- Inject [`Clock`](library/shared/ports.py) protocol
- Production: `SystemClock`. Tests: `FakeClock(fixed_time)`

### Logger port

- Use cases never `import structlog`
- Inject [`Logger`](library/shared/ports.py) protocol
- Production: structlog-backed via [`get_logger`](library/shared/adapters.py)
- Request context (`request_id`, `method`, `path`) is auto-bound via `contextvars.merge_contextvars`

### PasswordHasher port

- [`PasswordHasher`](library/shared/ports.py) in `shared.ports`
- Production: `Argon2PasswordHasher` (argon2-cffi, OWASP defaults) in [`shared/adapters.py`](library/shared/adapters.py)
- Tests: `FakePasswordHasher` producing deterministic `"hashed:<password>"`

### Two JWT ports (ISP)

- `auth.ports.TokenIssuer` — access + refresh tokens
- `member.ports.VerificationTokenIssuer` — email-verification tokens (`purpose=verify_email` claim)
- Same `JWT_SECRET_KEY`, distinct `purpose` claim — tokens for one purpose are rejected by endpoints for another

### Notifier as business port

- [`Notifier`](library/notification/ports.py) sends a [`Notification`](library/notification/models.py) VO (`subject`, `body`) — **not** an "email service"
- Channel (email / SMS / push) is the impl's concern
- Use case never knows what channel is used

### Decorator pattern for caching

- `CachedBookRepository` / `CachedMemberRepository` wrap any repository
- Cache layer abstracted behind [`Cache`](library/shared/ports.py) protocol with `RedisCache` and `InMemoryCache` impls (both in [`shared/adapters.py`](library/shared/adapters.py))
- Cache **invalidates on writes**, populates on `find_by_id`

### Pydantic Settings — fail-fast

- All config in [`Settings`](library/shared/config.py) with `extra="forbid"`
- `Literal`-typed enums for `LOG_LEVEL`, `LOG_FORMAT`, `JWT_ALGORITHM`
- `Field(min_length=...)` / `Field(gt=0)` validators
- URL fields have prefix validators

---

## Exception taxonomy

Two base classes in [`shared/exceptions.py`](library/shared/exceptions.py):
- `DomainError` — broken invariants
- `ApplicationError` — workflow / policy violations

Both subclasses are co-located per module in `<module>/exceptions.py`:

| Class | Base | Module | HTTP status |
|---|---|---|---|
| `BookNotFound` | DomainError | book | 404 |
| `BookNotAvailable` | DomainError | book | 409 |
| `BookAlreadyExists` | ApplicationError | book | 409 |
| `MemberNotFound` | DomainError | member | 404 |
| `InvalidVerificationToken` | DomainError | member | 401 |
| `MemberAlreadyExists` | ApplicationError | member | 409 |
| `MemberNotVerified` | ApplicationError | member | 403 |
| `LoanNotFound` | DomainError | loan | 404 |
| `InvalidAccessToken` | DomainError | auth | 401 |
| `RefreshTokenInvalid` / `Expired` / `Revoked` / `NotFound` | DomainError | auth | 401 |
| `InvalidCredentials` | ApplicationError | auth | 401 |

`ValueError` raised from VO validation → 422 (mapped centrally in [`shared/api/main.py`](library/shared/api/main.py)).

**Routes never `try/except`.** They let exceptions bubble.

---

## File organization rules

- **One file per use case** in `<module>/use_cases/` — each file contains both the Command dataclass and the UseCase class
- **Pydantic request schemas** live with their route in `<module>/api/routes/<verb>_<entity>.py`; the shared response schema (`<Entity>Response`) lives in `<module>/api/schemas.py`
- **SQL tables** are declared in `<module>/repositories.py` at module top, registered against the shared `MetaData()` from [`shared/adapters.py`](library/shared/adapters.py)
- **Repository protocols** in `<module>/ports.py`, **never** in `repositories.py`
- **Composition root** is [`shared/api/dependencies.py`](library/shared/api/dependencies.py) — the **only** place that imports concretes across modules for the cross-module port bridges
- **Feature-private DI providers** (e.g., `get_book_repo`, `get_token_issuer`, `get_verification_token_issuer`) live in each module's `api/dependencies.py`. Other modules can import these directly; only true cross-module port wiring stays in shared

---

## Tests

402 tests total. Test tree mirrors source structure: `tests/<module>/test_models.py`, `tests/<module>/repositories/`, `tests/<module>/use_cases/`, `tests/<module>/api/`.

- **Test runner:** `pytest -W error` (warnings = failures)
- **Asyncio mode:** `auto` (from `pyproject.toml`)
- **Contract tests** are parametrized over every repository impl: `sql` for all modules, plus `cache_redis` / `cache_in_memory` for book and member
- **Protocol satisfaction:** each adapter has a `test_satisfies_<port>_protocol` assertion via `isinstance(adapter, Port)` (Protocols are decorated `@runtime_checkable` where this check exists — see `tests/book/repositories/test_contract.py`)
- **Cross-feature fixtures** in [`tests/conftest.py`](tests/conftest.py): `valid_*`, `clock`, `token_issuer`, `credential_verifier`, `verification_token_issuer`, `client`. The repo fixtures (`book_repo`, `member_repo`, `loan_repo`, `refresh_token_repo`) are `Sql*Repository` instances backed by a fresh `:memory:` SQLite engine per test, sharing one `db_session` so writes through one repo are visible through another
- **No real I/O in unit tests** — SQLite `:memory:` for persistence, `FakeClock` for time, `fakeredis` for Redis, `FakePasswordHasher` for hashing, `FakeNotifier` for outbound notifications

---

## Commands

| Task | Command |
|---|---|
| Install | `pip install -e ".[dev]"` |
| Run tests (warnings-as-errors) | `pytest -W error` |
| Lint (must be clean) | `ruff check library tests` |
| Type-check (strict, must be clean) | `mypy library tests` |
| Spell-check | `codespell --skip="*.lock,.git,__pycache__,.venv,*.egg-info"` |
| Security: deps | `pip-audit --skip-editable` |
| Security: licenses | `pip-licenses --fail-on="GPL;LGPL;AGPL"` |
| Run API locally | `uvicorn library.shared.api.main:app --reload` |
| Docker dev stack | `docker compose up --build` |

CI runs all of the above on every push / PR. See [.github/workflows/ci.yml](.github/workflows/ci.yml) and the [`/verify`](.claude/skills/verify/SKILL.md) skill, which mirrors CI step-for-step.

Code-level security (the old `bandit -r library` step) is now inside `ruff check` via the `S` rule family.

---

## TypeScript-style standards (Python edition)

- **Python 3.12+** — `match` statements, `PEP 695` generics permitted
- **Async everywhere** — repositories, use cases, services. Sync handlers are an anti-pattern
- **Type hints mandatory** on all public functions, methods, class attributes. `mypy strict` enforces this in `library/`; the `tests.*` override drops the "every function needs `-> None`" noise but keeps real correctness signals
- **Avoid `Any`** — use `object`, `unknown` workarounds, or precise unions
- **Avoid `# type: ignore`** — fix the type instead. The handful of legitimate ignores in the tree all have inline comments explaining the specific external typing gap they paper over
- **Avoid `# noqa: ...`** — fix the underlying issue. The handful in the tree (e.g., `setattr` on a frozen-dataclass test where direct assignment fails mypy) all carry an inline comment
- **Prefer named types** over deep inline unions for repeated structures
- **Code, identifiers, comments, commit messages — always English.** Enforced by ruff's `RUF001/002/003` (ambiguous unicode in string literals / docstrings / comments) which catches Cyrillic look-alikes that read as ASCII

---

## Verification checklist before completing a task

Before considering work done, AI agents must verify:

1. ✅ **No layer violations** — `models.py` / `ports.py` don't import from `repositories.py`; `use_cases/` doesn't import from `repositories.py` or `api/`
2. ✅ **No ORM leakage** — repositories return domain entities, not SQL rows
3. ✅ **`pytest -W error`** runs clean (all 402 tests + zero warnings)
4. ✅ **`ruff check library tests`** reports "All checks passed!"
5. ✅ **`mypy library tests`** reports "Success: no issues found"
6. ✅ **No `datetime.now()`** outside the `Clock` impl in `shared/adapters.py`
7. ✅ **No `try/except`** in routes
8. ✅ **New use cases** are classes with single `execute(command)`, in `<module>/use_cases/<verb>_<noun>.py`, with the Command DTO co-located
9. ✅ **New repositories** carry a Protocol-satisfaction test and pass the parametrized contract test
10. ✅ **HTTP responses** use Pydantic schemas from `<module>/api/schemas.py` (shared) or `<module>/api/routes/<route>.py` (route-local), not raw dicts or domain entities

Or just invoke [`/verify`](.claude/skills/verify/SKILL.md) — it runs the same six commands CI runs.

---

## What this project deliberately does NOT do

If an agent is tempted to add any of the following, **stop and confirm with the human first**:

- ❌ **Domain Event Bus** — direct calls (`Notifier.send`) are correct until there are two subscribers
- ❌ **CQRS / Event Sourcing** — read/write models are the same; no event log
- ❌ **Generic `BaseEntity`** — each entity defines its own `__eq__` / `__hash__`
- ❌ **Unit of Work** — session-per-request via FastAPI DI already carries transactional consistency; UoW was added and removed
- ❌ **RBAC / role system** — authentication exists, authorization is one `is_verified` gate, no roles
- ❌ **Per-use-case slicing** — modules are per bounded subdomain, not per use case
- ❌ **Pagination / filtering on list endpoints** — out of scope
- ❌ **Token blocklist on access tokens** — they're 15-min stateless; only refresh tokens are revocable
- ❌ **Reintroducing the deep `domain/` `application/` `infrastructure/` `presentation/` layer-folder layout** — the flat per-module shape is deliberate; the dependency rule is encoded by file, not by directory

**The lesson behind these choices:** a pattern earns its place by solving present pain, not by appearing in textbooks.

---

## When in doubt

1. Re-read the README — every architectural claim there is enforced by a test
2. Read tests in the same area as your change — they describe expected behavior
3. Run `/verify` before considering work done
4. If you want to introduce a pattern not used elsewhere in the codebase, **ask first**
