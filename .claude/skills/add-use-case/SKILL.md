---
name: add-use-case
description: Generate a new use case inside an existing module, following the project's flat per-module conventions.
---

# Add Use Case

When the human says "add use case X to module Y" (or "add ability to do X for entity Y"), follow this skill **before writing any code**.

## Pre-flight

1. Read [AGENTS.md](../../../AGENTS.md) — confirm the Dependency Rule (file-level) and exception taxonomy.
2. Identify the **module** (`book/`, `member/`, `loan/`, `auth/`, `notification/`). If the use case naturally spans multiple modules, it lives in the **consumer** module and pulls ports from the others.
3. Pick a **reference** existing use case to mirror — they all follow the same shape:
   - Read-side reference: [`read_book.py`](../../../library/book/use_cases/read_book.py)
   - Write-side reference: [`add_book.py`](../../../library/book/use_cases/add_book.py)
   - Multi-aggregate reference: [`borrow_book.py`](../../../library/loan/use_cases/borrow_book.py)

## Workflow

### Step 1 — Confirm intent with the human

Before writing code, surface these decisions in **one short message**:

- Which module owns this use case?
- Does it mutate state (writes / raises domain exceptions) or read-only?
- Does it cross modules? Which ports does it need?
- **Does it emit a domain event?** If the use case completes a meaningful state transition that another module might react to (registration, borrow, return, login), publish via `EventPublisher` instead of calling a side-effect port directly. The use case stays thin; subscribers (in the consumer module's `subscribers.py`) own the reaction. See the "Event-driven side-effects" section of [AGENTS.md](../../../AGENTS.md) and the reference: [`AddMemberUseCase`](../../../library/member/use_cases/add_member.py) → [`SendVerificationEmailOnRegistration`](../../../library/notification/subscribers.py).
- Authentication required (Bearer + verified)? `/auth` routes are public; `/loans` is auth-gated via `get_verified_member` on the aggregator router.

Wait for confirmation. **Do not assume.**

### Step 2 — Create the use case file

File path: `library/<module>/use_cases/<verb>_<noun>.py`

**Both the Command DTO and the UseCase class live in the same file.** Skeleton (mirror style precisely):

```python
from dataclasses import dataclass

from library.<module>.exceptions import <ApplicationException>, <DomainException>
from library.<module>.models import <Entity>
from library.<module>.ports import <EntityRepository>
from library.shared.ports import Clock, Logger  # only if needed


@dataclass(frozen=True)
class <Verb><Noun>Command:
    # only fields the use case needs; not the HTTP shape
    ...


class <Verb><Noun>UseCase:
    def __init__(
        self,
        <entity>_repo: <EntityRepository>,
        clock: Clock,           # only if needed
        logger: Logger,         # only if needed
    ):
        self._<entity>_repo = <entity>_repo
        self._clock = clock
        self._logger = logger

    async def execute(self, command: <Verb><Noun>Command) -> <ReturnType>:
        # 1. Load
        # 2. Validate / check invariants → raise domain/application exceptions
        # 3. Mutate / compute (pure)
        # 4. Persist (create vs update — explicit)
        # 5. Publish domain event (if meaningful transition) + other side-effects (Logger)
        # 6. Return
        ...
```

**Rules:**
- Command DTO is a **frozen dataclass**; fields only — no HTTP types, no `Depends()`.
- All dependencies injected via constructor — no `Depends()` inside the class.
- `async` body (everything is async in this codebase).
- **Never call `datetime.now()`** — use `self._clock.now()`.
- **Never `import structlog`** — use `self._logger.info(...)`.
- **Never catch exceptions to convert them** — raise domain/application exceptions, let the HTTP layer map.
- **`create` vs `update` on repositories** — no upserts.
- **Never `from library.<module>.repositories import ...`** — use cases consume Ports, not impls.

### Step 3 — Wire feature-local DI provider

Edit `library/<module>/api/dependencies.py` (NOT shared):

```python
def get_<verb>_<noun>_use_case(
    <entity>_repo: <EntityRepository> = Depends(get_<entity>_repo),
    clock: Clock = Depends(get_clock),
) -> <Verb><Noun>UseCase:
    return <Verb><Noun>UseCase(<entity>_repo, clock)
```

Cross-cutting ports come from `library.shared.api.dependencies`: `get_clock`, `get_password_hasher`, `get_session`, `get_cache`, `get_event_publisher`. Module-owned ports (e.g., `VerificationTokenIssuer` from `member/`) come from that owner module's `api/dependencies.py`. The shared composition root is only for cross-module port BRIDGES (`get_credential_verifier`, `get_book_availability`).

### Step 4 — Add HTTP route (if exposed via API)

Create `library/<module>/api/routes/<verb>_<entity>.py`:

```python
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from library.<module>.api.dependencies import get_<verb>_<noun>_use_case
from library.<module>.api.schemas import <Entity>Response
from library.<module>.use_cases.<verb>_<noun> import (
    <Verb><Noun>Command,
    <Verb><Noun>UseCase,
)


class <Verb><Entity>Request(BaseModel):
    # HTTP request shape; lives with the route
    ...


router = APIRouter(prefix="/<entities>", tags=["<entity>"])


@router.post("", status_code=201)
async def <verb>_<entity>(
    payload: <Verb><Entity>Request,
    use_case: <Verb><Noun>UseCase = Depends(get_<verb>_<noun>_use_case),
) -> <Entity>Response:
    result = await use_case.execute(<Verb><Noun>Command(...))
    return <Entity>Response.from_domain(result)
```

Then register it in `library/<module>/api/__init__.py`:

```python
router.include_router(<verb>_<entity>.router)
```

**Routes:**
- Never `try/except` — let exceptions bubble.
- Convert HTTP request → command via plain dataclass construction.
- Convert domain entity → response via `<Entity>Response.from_domain(...)`.

### Step 5 — Write tests

File path: `tests/<module>/use_cases/test_<verb>_<noun>.py`

```python
import pytest

from library.<module>.exceptions import <DomainException>
from library.<module>.ports import <EntityRepository>
from library.<module>.use_cases.<verb>_<noun> import (
    <Verb><Noun>Command,
    <Verb><Noun>UseCase,
)


class Test<Verb><Noun>UseCase:
    async def test_<verb>_succeeds(
        self, <entity>_repo: <EntityRepository>, ...
    ):
        use_case = <Verb><Noun>UseCase(<entity>_repo, ...)
        result = await use_case.execute(<Verb><Noun>Command(...))
        assert ...

    async def test_<verb>_raises_on_missing(self, <entity>_repo):
        use_case = <Verb><Noun>UseCase(<entity>_repo, ...)
        with pytest.raises(<DomainException>):
            await use_case.execute(<Verb><Noun>Command(...))
```

**Test rules:**
- Use the **conftest-provided repo fixtures** (`book_repo`, `member_repo`, `loan_repo`, `refresh_token_repo`) from [`tests/conftest.py`](../../../tests/conftest.py) — they're `Sql*Repository` instances backed by a fresh `:memory:` SQLite engine per test, sharing one `db_session`.
- Use **`FakeClock`** (fixed timestamp) for time-dependent behavior.
- Test happy path + at least one error path per branch.
- Test names: `test_<verb>_<noun>_<expectation>` (one assertion per test where possible).

### Step 6 — Add an HTTP test (only if a route was added)

File path: `tests/<module>/api/test_api.py` (extend the existing file; don't create a new one per route).

```python
async def test_<verb>_endpoint_returns_201(client, valid_<thing>):
    response = await client.post("/<resource>", json={...})
    assert response.status_code == 201
    assert response.json() == {...}


async def test_<verb>_endpoint_returns_404_when_missing(client):
    response = await client.post("/<resource>", json={...})
    assert response.status_code == 404
```

Use the `client` fixture from [`tests/conftest.py`](../../../tests/conftest.py) — it's an `httpx.AsyncClient` over `ASGITransport` (no real network).

### Step 7 — Run verify

Run [`/verify`](../verify/SKILL.md). All six steps (pytest, ruff, mypy, codespell, pip-audit, pip-licenses) must pass clean.

## Reference: shape of a complete use case

[`AddMemberUseCase`](../../../library/member/use_cases/add_member.py) is the canonical example — depends on `MemberRepository`, `PasswordHasher`, and `EventPublisher`; validates duplicates, persists, then publishes `MemberRegistered`. The welcome-email side-effect lives in [`SendVerificationEmailOnRegistration`](../../../library/notification/subscribers.py), NOT in the use case — the use case stays free of email/token concerns. Read both and mirror when your use case has its own meaningful state transition.

## Do not

- ❌ Put SQL strings, Pydantic schemas, or `Depends()` inside the use case class
- ❌ Mutate global state
- ❌ Call `datetime.now()` / `random.random()` / `logger.info()` directly
- ❌ `try/except` to convert exceptions — raise domain/application, let HTTP layer map
- ❌ Skip writing the test — every use case has at least 2 tests
- ❌ Put the Command DTO in a separate file (it lives with the UseCase in the same module file)
- ❌ Import from `<module>.repositories` in the use case — use cases consume Ports, not impls
