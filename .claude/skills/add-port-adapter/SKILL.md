---
name: add-port-adapter
description: Generate a new Port (Protocol) + Adapter pair, or add a new Adapter for an existing Port. Covers cross-cutting and slice-local ports — anything that's not a Repository.
---

# Add Port + Adapter

When the human says "add a port for X" / "add a new SMS notifier alongside the email one" / "extract a Clock port" / "swap Argon2 for Bcrypt":

This skill covers **everything that is a Port + Adapter except Repository** (which has its own skill: [`/add-repository-impl`](../add-repository-impl/SKILL.md)).

Typical use cases:
- **New impl for existing port:** `BcryptPasswordHasher` alongside `Argon2PasswordHasher`; `SmsNotifier` alongside `EmailNotifier`; `LogglyLogger` alongside `StructlogLogger`
- **New port + first impl:** introduce `Clock`, `Random`, `IdGenerator`, `RateLimiter`, `MetricsRecorder`
- **Extract a Port from a direct dependency:** when a domain class started using `requests` / `smtplib` / `boto3` directly

## Pre-flight

1. Read [AGENTS.md](../../../AGENTS.md) — Dependency Rule, port placement rules.
2. Look at reference Ports + Adapters in the codebase:

| Port | Lives in | Impls |
|---|---|---|
| `Clock` | `shared/ports.py` | `SystemClock` in `shared/adapters.py` |
| `PasswordHasher` | `shared/ports.py` | `Argon2PasswordHasher` in `shared/adapters.py` |
| `Logger` | `shared/ports.py` | structlog-backed via `get_logger` in `shared/adapters.py` |
| `Cache` | `shared/ports.py` | `RedisCache` + `InMemoryCache` in `shared/adapters.py` |
| `Notifier` | `notification/ports.py` | `EmailNotifier` in `notification/email_notifier.py` |
| `TokenIssuer` | `auth/ports.py` | `PyJWTTokenIssuer` in `auth/repositories.py` |
| `VerificationTokenIssuer` | `member/ports.py` | `PyJWTVerificationTokenIssuer` in `member/repositories.py` |
| `CredentialVerifier` | `auth/ports.py` | `MemberCredentialVerifier` in `member/repositories.py` (cross-module!) |
| `BookAvailability` | `book/ports.py` | `LoanBookAvailability` in `loan/repositories.py` (cross-module!) |

## Workflow

### Step 1 — Confirm scope with the human

Ask **only what's not obvious**:

- Is this a **new port** (create + first impl) or a **new impl** for an existing port?
- What's the port name and method signatures? (For new ports — a one-line description of the responsibility.)
- Where does the port live? — see decision tree below.
- Where does the impl live? — see decision tree below.
- Does it have an in-memory / fake variant for tests?

### Step 2 — Decide where the Port lives

```
Who consumes this port (use cases from which modules)?
│
├── Multiple modules (e.g., Clock, Logger, PasswordHasher, Cache)
│   → shared/ports.py
│
├── Single module, and impl uses no other module's data
│   → <module>/ports.py
│
└── Single module (consumer), but impl needs another module's data
    (e.g., auth needs CredentialVerifier impl that reads from member)
    → <consumer-module>/ports.py
    → impl in <provider-module>/repositories.py  ← asymmetric, by design
```

**Rule:** the port lives **with the consumer**. The impl can live anywhere that has the data — even another module's `repositories.py`. This is exactly the `CredentialVerifier` pattern (auth port, member impl) and `BookAvailability` pattern (book port, loan impl) documented in the README.

### Step 3 — Decide where the Adapter lives

```
What backs this impl?
│
├── Library / external service (Argon2, Stripe, Resend, Postgres)
│   → If port is in shared/      → shared/adapters.py
│   → If port is in <module>/    → <module>/repositories.py (or its own file
│                                  if the module is minimal, like notification's
│                                  email_notifier.py)
│
├── Another module's data (CredentialVerifier reading Member)
│   → Provider module's repositories.py
│
└── In-memory / fake (for tests)
    → tests/conftest.py (the FakeClock / FakePasswordHasher / FakeNotifier pattern)
```

### Step 4 — Generate the Port file (or add to existing `ports.py`)

For a port living in shared (cross-cutting), append to [`library/shared/ports.py`](../../../library/shared/ports.py):

```python
from typing import Protocol, runtime_checkable


@runtime_checkable
class <Name>(Protocol):
    """<One-line responsibility>.

    <Multi-line elaboration if needed — what it abstracts, what invariants
    implementations must preserve.>
    """

    async def <method>(self, <args>) -> <return>: ...
    # ... other methods ...
```

For a port living in a module, append to `library/<module>/ports.py`:

```python
from typing import Protocol, runtime_checkable

from library.<module>.models import <DomainType>   # if needed


@runtime_checkable
class <Name>(Protocol):
    async def <method>(self, <arg>: <DomainType>) -> <return>: ...
```

**Rules:**
- `Protocol` from `typing` — never `ABC` (the project uses structural subtyping)
- `@runtime_checkable` so a test can do `isinstance(adapter, Port)` to verify conformance
- Most methods `async` (this codebase is async everywhere — sync methods only for hashing/serialization)
- Method signatures use **domain types**, not infrastructure types — no `dict`, no `JSON`, no SQL strings, no `Response` objects
- Don't add a default impl — Protocol bodies are `...`

### Step 5 — Generate the Adapter

Add to the module's `repositories.py` (or `shared/adapters.py` for cross-cutting ports). Mirror the structure of an existing adapter in the same file.

```python
# library/<location>/repositories.py  (or shared/adapters.py)
from library.<location-of-port>.ports import <Port>
# ... other imports ...


class <AdapterName>:
    """<One-line description: which port + which backend>."""

    def __init__(self, <config-args>):
        # store config, set up clients
        ...

    async def <method>(self, <args>) -> <return>:
        # actual implementation
        ...
```

**Rules:**
- **No `implements <Port>`** — structural typing in Python. The class just has matching methods.
- Constructor takes config / dependencies — never global state
- Domain types in / domain types out — external client types stay private
- If the adapter wraps a library, **isolate** the library — no `requests.Response`, `redis.Redis`, etc. escaping public methods

### Step 6 — Generate the test file

For unit tests (against the impl directly):

```python
# tests/<slice>/infrastructure/test_<adapter-name>.py
import pytest
from library.<slice>.infrastructure.<adapter-name> import <AdapterName>


@pytest.fixture
def adapter():
    return <AdapterName>(<config>)


async def test_<adapter>_satisfies_contract(adapter):
    # exercise public methods, assert return shape
    ...


async def test_<adapter>_handles_<edge>(adapter):
    # one test per branch / error case
    ...
```

**If the port has multiple impls** (like `Notifier` with `EmailNotifier` + `SmsNotifier` + a future `PushNotifier`), consider a **parametrized contract test** like the repository contract tests:

```python
# tests/<slice>/infrastructure/conftest.py
@pytest.fixture(params=["email", "sms", "push"])
def notifier(request):
    if request.param == "email":
        return EmailNotifier(...)
    elif request.param == "sms":
        return SmsNotifier(...)
    # ...


# tests/<slice>/infrastructure/test_notifier_contract.py
async def test_send_returns_none(notifier):
    result = await notifier.send(Notification(...))
    assert result is None  # or whatever the protocol promises
```

This is **LSP enforcement** — every impl must obey the same observable contract.

### Step 7 — Wire in composition root or module-local DI

If the port + impl are both inside a single module → wire in the module's `api/dependencies.py`. If the impl bridges modules (the asymmetric pattern) → wire in [`library/shared/api/dependencies.py`](../../../library/shared/api/dependencies.py) (composition root).

```python
def get_<port-name>(
    settings: Settings = Depends(get_settings),
    # ... other deps ...
) -> <PortType>:
    return <AdapterName>(
        <config-from-settings>,
    )
```

If the port already has a provider and you're adding a **new impl** as an alternative — switch via config:

```python
def get_password_hasher(
    settings: Settings = Depends(get_settings),
) -> PasswordHasher:
    if settings.password_hasher == "bcrypt":
        return BcryptPasswordHasher(rounds=settings.bcrypt_rounds)
    return Argon2PasswordHasher()  # default
```

Add the new setting to [`shared/config.py`](../../../library/shared/config.py) (`Literal` typed, with a default).

### Step 8 — Fake / in-memory variant for tests

Most ports need a deterministic fake for use case tests. Examples already in the codebase:

- `FakeClock(fixed_now=datetime(2026, 1, 1))` — for time-dependent logic
- `FakePasswordHasher` returns `f"hashed:{password}"` — deterministic, no real Argon2 cost
- `InMemoryCache` — LRU dict, no Redis

Add a fake **only if** there's a use case test that needs it. Don't pre-emptively create fakes.

If creating, place it next to the real impl:
- `library/shared/infrastructure/fake_password_hasher.py` (or in `tests/` if test-only)

### Step 9 — Verify

```sh
/verify
```

Then [`/git-commit`](../git-commit/SKILL.md). Conventional Commits scope = the consumer slice (`feat(member): add Bcrypt password hasher alternative`) or `shared` for cross-cutting (`feat(shared): add Random port`).

## Decision examples (worked)

### Example A — Add `SmsNotifier` alongside `EmailNotifier`

- **Port:** `Notifier` already exists in `notification/domain/services.py`. Don't modify.
- **Adapter:** New `SmsNotifier` in `notification/infrastructure/sms_notifier.py`.
- **Composition:** Either swap-via-config (`settings.notifier == "sms"`) **or** compose both via a `MultiNotifier`. Ask the human.
- **Tests:** Add `SmsNotifier` to the parametrized fixture if a contract test exists.

### Example B — Extract `IdGenerator` port from inline `uuid4()`

- **Port:** Cross-cutting. New file `shared/application/id_generator.py` with `class IdGenerator(Protocol): def uuid(self) -> UUID: ...`
- **Adapter:** `shared/infrastructure/id_generator.py` with `class UuidGenerator: def uuid(self): return uuid4()`.
- **Use cases:** find usages of `uuid4()` in `application/use_cases/`, replace with constructor-injected `IdGenerator`.
- **Tests:** Create `FakeIdGenerator` returning a sequence (`uuid_001`, `uuid_002`, ...). Use case tests get predictable IDs.

### Example C — Add `MetricsRecorder` port for observability

- **Port:** Cross-cutting. `shared/application/metrics.py` with `record_counter`, `record_gauge`, `record_histogram` methods.
- **Adapter:** `shared/infrastructure/prometheus_metrics.py`. In tests: `InMemoryMetricsRecorder` that just appends to a list.
- **Use cases:** opt in by injecting the port. Don't retroactively add to every use case.

## Anti-patterns

| Pattern | Why it's wrong | Fix |
|---|---|---|
| Port in `infrastructure/` | Ports live with the consumer, not the implementation | Move to `<slice>/domain/services.py` or `shared/application/` |
| Port returns library type (`requests.Response`) | Leaks the library into the consumer | Return domain type or primitives |
| Adapter implements port via inheritance (`class X(Port):`) | Python uses structural typing — `implements` is noise | Just match the method signatures |
| Hardcoded config in adapter (`self.host = "localhost"`) | Untestable, unconfigurable | Take config via constructor |
| Two ports doing the same thing in different slices | Should be one port in `shared/` | Consolidate |
| ABCs instead of `Protocol` | This codebase uses Protocol throughout for ports | Use `Protocol` |
| Port has too many methods (5+) | Probably violates ISP | Split into role-specific ports (see `TokenIssuer` vs `VerificationTokenIssuer`) |

## When to add a port vs. inline the dependency

**Add a port when:**
- ✅ There are (or will be) 2+ implementations (production + test fake; or production + alternative backend)
- ✅ Crossing the domain ↔ infrastructure boundary
- ✅ External I/O is involved (HTTP, DB, filesystem, time, randomness)
- ✅ You want deterministic tests without mocking the world

**Don't add a port when:**
- ❌ One implementation, no foreseeable second, no testability win (YAGNI)
- ❌ Standard library functions you'd never swap (`math.sqrt`, `str.upper`)
- ❌ Pure-domain helpers — they're already pure-functional

## Resume one-liner

> **Port + Adapter pair. Port = `Protocol` in `<consumer>/domain/services.py` (slice-local) or `shared/application/<name>.py` (cross-cutting). Adapter = concrete class in `<slice>/infrastructure/` (or `shared/infrastructure/` or another slice's infra if cross-slice). Structural typing — no `implements`. Wire via composition root, swap impls via config. Repository has its own skill (`/add-repository-impl`); everything else uses this one.**
