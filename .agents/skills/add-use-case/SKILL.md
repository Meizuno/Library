---
name: add-use-case
description: Generate a new use case inside an existing bounded-context slice, following the project's DDD layered conventions.
---

# Add Use Case

When the human says "add use case X to slice Y" (or "add ability to do X for entity Y"), follow this skill **before writing any code**.

## Pre-flight

1. Read [AGENTS.md](../../../AGENTS.md) — confirm the Dependency Rule and exception taxonomy.
2. Identify the **slice** (`book/`, `member/`, `loan/`, `auth/`, `notification/`). If the use case naturally spans multiple slices, it lives in the **consumer** slice and pulls ports from the others.
3. Pick a **reference** existing use case to mirror — they all follow the same shape:
   - Read-side reference: [`read_book.py`](../../../library/book/application/use_cases/read_book.py)
   - Write-side reference: [`add_book.py`](../../../library/book/application/use_cases/add_book.py)
   - Multi-aggregate reference: [`borrow_book.py`](../../../library/loan/application/use_cases/borrow_book.py)

## Workflow

### Step 1 — Confirm intent with the human

Before writing code, surface these decisions in **one short message**:

- Which slice owns this use case?
- Does it mutate state (writes/raises domain exceptions) or read-only?
- Does it cross slices? Which ports does it need?
- Authentication required (Bearer + verified)? `/auth` and `/loans` endpoints already use `get_verified_member`.

Wait for confirmation. **Do not assume.**

### Step 2 — Create the Command DTO

Add to `library/<slice>/application/commands.py`:

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class <Verb><Noun>Command:
    # only fields the use case needs; not the HTTP shape
    ...
```

Commands are **frozen dataclasses**, contain only fields the use case consumes. Do **not** put `request: Request` or HTTP-shaped types here.

### Step 3 — Create the use case class

File path: `library/<slice>/application/use_cases/<verb>_<noun>.py`

Skeleton (mirror style precisely):

```python
from library.<slice>.domain import <Entity>, <Repository>
from library.<slice>.application.commands import <Verb><Noun>Command
from library.<slice>.application.exceptions import <ApplicationException>
from library.<slice>.domain.exceptions import <DomainException>
from library.shared.application.clock import Clock        # if time is needed
from library.shared.application.logger import Logger      # if logging is needed


class <Verb><Noun>UseCase:
    def __init__(
        self,
        <entity>_repo: <Repository>,
        clock: Clock,         # only if needed
        logger: Logger,       # only if needed
    ):
        self._<entity>_repo = <entity>_repo
        self._clock = clock
        self._logger = logger

    async def execute(self, command: <Verb><Noun>Command) -> <ReturnType>:
        # 1. Load
        # 2. Validate / check invariants → raise domain/application exceptions
        # 3. Mutate / compute (pure)
        # 4. Persist (create vs update — explicit)
        # 5. Side-effects (Notifier, Logger)
        # 6. Return
        ...
```

**Rules:**
- All dependencies via constructor — no `Depends()` inside the class
- `async` body (everything is async in this codebase)
- **Never call `datetime.now()`** — use `self._clock.now()`
- **Never `import structlog`** — use `self._logger.info(...)`
- **Never catch exceptions to convert them** — raise domain/application exceptions, let HTTP layer map
- **`create` vs `update` on repositories** — no upserts

### Step 4 — Export from `__init__.py`

Add to `library/<slice>/application/use_cases/__init__.py`:

```python
from .<verb>_<noun> import <Verb><Noun>UseCase

__all__ = [..., "<Verb><Noun>UseCase"]
```

### Step 5 — Wire in composition root

Edit [`library/shared/presentation/api/dependencies.py`](../../../library/shared/presentation/api/dependencies.py):

```python
def get_<verb>_<noun>_use_case(
    <entity>_repo: <Repository> = Depends(get_<entity>_repository),
    clock: Clock = Depends(get_clock),
) -> <Verb><Noun>UseCase:
    return <Verb><Noun>UseCase(<entity>_repo=<entity>_repo, clock=clock)
```

### Step 6 — Add HTTP endpoint (if exposed via API)

Edit `library/<slice>/presentation/api/router.py`:

```python
@router.post("/<resource>", status_code=201)
async def <verb>_<resource>(
    payload: <Verb><Resource>Schema,
    use_case: <Verb><Resource>UseCase = Depends(get_<verb>_<resource>_use_case),
) -> <Resource>Response:
    result = await use_case.execute(payload.to_command())
    return <Resource>Response.from_entity(result)
```

**Routers:**
- Never `try/except` — let exceptions bubble
- Convert request DTO → command via `.to_command()` method on schema
- Convert entity → response DTO via `.from_entity()` classmethod

### Step 7 — Write tests at the application layer

File path: `tests/<slice>/application/test_<verb>_<noun>.py`

```python
import pytest
from library.<slice>.application.use_cases.<verb>_<noun> import <Verb><Noun>UseCase
from library.<slice>.application.commands import <Verb><Noun>Command
from library.<slice>.application.exceptions import <ApplicationException>
from library.<slice>.infrastructure.in_memory_repository import InMemory<Entity>Repository


@pytest.fixture
def use_case(<entity>_repo, clock, logger):
    return <Verb><Noun>UseCase(<entity>_repo=<entity>_repo, clock=clock, logger=logger)


async def test_<verb>_<noun>_succeeds(use_case, <fixtures>):
    result = await use_case.execute(<Verb><Noun>Command(...))
    assert ...


async def test_<verb>_<noun>_raises_on_missing(use_case):
    with pytest.raises(<DomainException>):
        await use_case.execute(<Verb><Noun>Command(...))
```

**Test rules:**
- Use **in-memory** repositories (no SQL in unit tests)
- Use **FakeClock** (fixed timestamp) for time-dependent behaviour
- Test happy path + at least one error path per branch
- Test names: `test_<verb>_<noun>_<expectation>` (one assertion per test where possible)

### Step 8 — Add an HTTP test (only if endpoint was added)

File path: `tests/<slice>/presentation/api/test_<verb>_<noun>_endpoint.py`

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

### Step 9 — Run verify

```sh
pytest -W error
pylint library tests
```

Both must pass clean. Pylint must score **10.00/10**. See `/verify` skill for full pre-commit checklist.

## Reference: shape of a complete use case

`AddMemberUseCase` ([library/member/application/use_cases/add_member.py](../../../library/member/application/use_cases/add_member.py)) is the canonical example — it touches multiple ports (`MemberRepository`, `PasswordHasher`, `VerificationTokenIssuer`, `Notifier`, `Clock`), validates duplicates, persists, sends welcome email. Read it and mirror.

## Do not

- ❌ Put SQL strings, Pydantic schemas, or `Depends()` inside the use case class
- ❌ Mutate global state
- ❌ Call `datetime.now()` / `random.random()` / `logger.info()` directly
- ❌ `try/except` to convert exceptions — raise domain/application, let HTTP layer map
- ❌ Skip writing the test — every use case has at least 2 tests
- ❌ Add Use Cases in `library/application/use_cases/` (legacy root path) — they go in slice-local `<slice>/application/use_cases/`
