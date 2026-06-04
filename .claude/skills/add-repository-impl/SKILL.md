---
name: add-repository-impl
description: Add a new persistence backend (e.g., MongoDB, file-based) for an existing repository protocol — must pass the contract test.
---

# Add Repository Implementation

When the human says "add MongoDB backend for Book" / "add file-based BookRepository" / "I want a new persistence backend for X":

## Pre-flight

1. Read [AGENTS.md](../../../AGENTS.md) — Repository pattern rules.
2. Identify the **protocol** to implement: `library/<module>/ports.py`
3. Read existing implementations to mirror style:
   - [`SqlBookRepository`](../../../library/book/repositories.py) — production reference, includes the soft-delete + filter-on-read pattern, uses `.returning(table.c.id) + scalar_one_or_none()` for DML
   - [`CachedBookRepository`](../../../library/book/repositories.py) — decorator pattern (different role; same file)
4. Read the **contract test** that **all** impls must pass: [`tests/book/repositories/conftest.py`](../../../tests/book/repositories/conftest.py) + [`tests/book/repositories/test_contract.py`](../../../tests/book/repositories/test_contract.py)

## Workflow

### Step 1 — Confirm scope with the human

- Which **entity** / repository? (`Book`, `Member`, `Loan`, `RefreshToken`)
- Which **backend** (`mongo`, `file`, `dynamodb`, etc.)?
- **Production or test-only**? Production impls require connection pooling, error handling. Test-only impls can be simpler.
- **Will it support caching** (i.e., be wrappable by `Cached<Entity>Repository`)? If yes, it must respect the cache invalidation contract (write methods must work even if cache layer is bypassed).

### Step 2 — Add the impl class

For a new backend, add a new class to `library/<module>/repositories.py` next to the existing `Sql*Repository`. (If the module has many repository impls and the file is getting unwieldy, split into a sibling file — but the default is co-location.)

Skeleton:

```python
from uuid import UUID

from library.<module>.exceptions import <Entity>NotFound
from library.<module>.models import <Entity>
from library.<module>.ports import <Entity>Repository


class <Backend><Entity>Repository:
    """<Backend>-backed implementation of <Entity>Repository protocol."""

    def __init__(self, <connection_or_client>):
        self._<conn> = <connection_or_client>

    async def find_by_id(self, id: UUID) -> <Entity> | None:
        # query
        row = await self._<conn>.<query>(id)
        if row is None:
            return None
        return self._row_to_entity(row)

    async def create(self, entity: <Entity>) -> None:
        # MUST raise on duplicate id — no upsert
        try:
            await self._<conn>.insert(self._entity_to_row(entity))
        except <DuplicateError>:
            raise ValueError(f"<Entity> {entity.id} already exists")

    async def update(self, entity: <Entity>) -> None:
        # MUST raise on missing id
        result = await self._<conn>.update(...)
        if result.modified_count == 0:
            raise <Entity>NotFound(str(entity.id))

    async def delete(self, id: UUID) -> None:
        # idempotent — delete-missing should NOT raise (per contract)
        await self._<conn>.delete(id)

    async def list_all(self) -> list[<Entity>]:
        rows = await self._<conn>.list(...)
        return [self._row_to_entity(r) for r in rows]

    # Mappers — keep them private. ORM/driver types NEVER escape this class.
    def _row_to_entity(self, row) -> <Entity>:
        return <Entity>(...)

    def _entity_to_row(self, entity: <Entity>) -> dict:
        return {...}
```

### Step 3 — Rules the impl MUST satisfy

These are **enforced by the contract test**:

1. **`create` raises `ValueError`** (or specific dup-error → mapped to ValueError) on duplicate id
2. **`update` raises `<Entity>NotFound`** when id missing — never silently insert
3. **`delete` is idempotent** — calling on missing id is OK (no raise)
4. **`find_by_id` returns `None`** when missing — never raise
5. **`list_all` returns `[]`** when empty — never `None`
6. **ORM / driver types stay inside the class** — return values are domain entities
7. **`create` followed by `find_by_id` returns the entity** — no async eventual consistency surprises in the contract test (use a snapshot or `await flush()` if your driver needs it)
8. **`update` reflected by next `find_by_id`** — same property as above
9. **Equality** — `find_by_id` returns an entity that `equals` what was saved (by id)

### Step 4 — Register in the contract test

Edit `tests/<module>/repositories/conftest.py`:

```python
@pytest.fixture(
    params=["sql", "<your_backend>"],   # ← add yours
    ids=["sql", "<your_backend>"],
)
async def empty_<entity>_repo(request, sql_<entity>_repo, <your_backend>_<entity>_repo):
    if request.param == "sql":
        yield sql_<entity>_repo
    elif request.param == "<your_backend>":
        yield <your_backend>_<entity>_repo
```

Add a fixture that provisions your backend (Docker-compose-managed for Mongo, tempfile for file, etc.).

### Step 5 — Optional: wire in module-local DI

If this is a **production-bound** impl (not test-only), edit `library/<module>/api/dependencies.py` (the feature-local `get_<entity>_repo`) to provide it as an alternative:

```python
def get_<entity>_repository(
    settings: Settings = Depends(get_settings),
    <client> = Depends(get_<backend>_client),
) -> <Entity>Repository:
    if settings.<backend>_enabled:
        return <Backend><Entity>Repository(<client>)
    # fallback
    return Sql<Entity>Repository(...)
```

(For most cases, only ONE production impl is active — switch via config.)

### Step 6 — Verify

Run [`/verify`](../verify/SKILL.md) — all six gates (pytest, ruff, mypy, codespell, pip-audit, pip-licenses) must pass clean.

If the contract test fails on the new impl, **the impl is wrong, not the test**. Fix the impl until it passes — that's the LSP guarantee.

## Reference

| Impl | File | What it demonstrates |
|---|---|---|
| SQL (book) | [`book/repositories.py`](../../../library/book/repositories.py) | Production-quality with SQLAlchemy Core, no ORM; soft-delete; `.returning(...) + scalar_one_or_none()` for DML detection |
| Cached (book) | [`book/repositories.py`](../../../library/book/repositories.py) | Decorator wrapping any `BookRepository`; cache invalidation on writes |
| SQL (loan) | [`loan/repositories.py`](../../../library/loan/repositories.py) | Hard delete (no soft-delete column); FK `ondelete="RESTRICT"` |

## Do not

- ❌ Skip the contract test — if it doesn't run on the new impl, the impl is not provably substitutable
- ❌ Return ORM rows / driver types from public methods — always map to domain entity
- ❌ Treat `create` as upsert — explicit `create` vs `update`
- ❌ Use `try/except` to silence errors that the contract expects to be raised
- ❌ Make `delete` raise on missing id — contract says it's idempotent
- ❌ Add private fields/methods that escape via `_field` — encapsulation is part of the contract
