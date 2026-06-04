---
name: add-value-object
description: Generate a new Value Object with self-validation, normalization, and tests.
---

# Add Value Object

When the human says "add VO X" / "add value object X" / "I need to model X as a domain primitive" (e.g., `PhoneNumber`, `Money`, `PostalCode`):

## Pre-flight

1. Read the [Value Objects](../../../library/book/models.py) reference (`ISBN`).
2. Read [Email and Password](../../../library/member/models.py) for more involved examples.
3. Confirm with the human:
   - Which **module** owns this VO? VOs live alongside the entity in `library/<module>/models.py`.
   - Does it have a **normalization** step (lowercase, trim, dash-strip)?
   - What are the **invariants** (length, format, allowed chars, range)?
   - Does it have **methods** (e.g., `domain()` on Email)? VOs with 5+ methods should consider being a class with behaviour, but in this codebase all VOs are minimal frozen dataclasses.

## VO shape

Every VO in this codebase follows this template exactly:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class <ValueObject>:
    value: str   # or other primitive / tuple of primitives

    def __post_init__(self) -> None:
        # 1. Normalize (if any) — must use object.__setattr__ because frozen
        normalized = self.value.strip().lower()   # whatever applies

        # 2. Validate — raise ValueError, NOT a custom exception
        if not normalized:
            raise ValueError("<VO> cannot be empty")
        if len(normalized) > 100:
            raise ValueError(f"<VO> too long: {len(normalized)} chars")
        # ...

        # 3. Assign normalized value back
        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value
```

**Rules:**
- `@dataclass(frozen=True)` — non-negotiable
- `__post_init__ -> None` (annotation required by mypy strict)
- Raise **`ValueError`** in `__post_init__` — NOT custom domain exceptions. The central HTTP handler in [`shared/api/main.py`](../../../library/shared/api/main.py) maps `ValueError` → 422.
- Use `object.__setattr__(self, "field", value)` to assign in `__post_init__` (frozen dataclasses block normal `self.field =`)
- Add `__str__` if the VO is commonly logged or formatted
- VO lives in the **same `models.py`** as the entity it relates to — keep the module flat

## Tests

File path: `tests/<module>/test_models.py` (same file as the entity tests — group by class).

```python
from dataclasses import FrozenInstanceError

import pytest

from library.<module>.models import <ValueObject>


class Test<ValueObject>:
    def test_normalizes_<aspect>(self):
        vo = <ValueObject>(" Example ")
        assert vo.value == "example"

    def test_accepts_<valid_case>(self):
        vo = <ValueObject>("valid-input")
        assert vo.value == "valid-input"

    @pytest.mark.parametrize("invalid", ["", "  ", "x" * 200, "invalid format"])
    def test_rejects_<aspect>(self, invalid: str):
        with pytest.raises(ValueError, match="<expected message fragment>"):
            <ValueObject>(invalid)

    def test_is_frozen(self):
        vo = <ValueObject>("example")
        with pytest.raises(FrozenInstanceError):
            # Direct assignment fails mypy's read-only check on frozen
            # dataclasses; setattr probes the runtime guard instead.
            setattr(vo, "value", "changed")  # noqa: B010

    def test_equality_by_value(self):
        assert <ValueObject>("x") == <ValueObject>("x")
        assert <ValueObject>("x") != <ValueObject>("y")
```

**Test rules:**
- Test **normalization** (trimming, lowercasing) — show that input is transformed
- Test **happy paths** (a few valid inputs)
- Test **invariant rejection** with `@pytest.mark.parametrize` for many invalid inputs; include `match="..."` in `pytest.raises` so the test pins down the specific error
- Test **frozen-ness** — use `setattr(vo, "value", ...)` inside `pytest.raises(FrozenInstanceError)` (direct `vo.value = ...` syntax fails mypy's read-only check). The `# noqa: B010` is required because ruff's B010 prefers direct assignment for constant attrs.
- Test **equality by value** (this is what makes it a VO, not Entity)

## Reference

| VO | File | What it demonstrates |
|---|---|---|
| `ISBN` | [book/models.py](../../../library/book/models.py) | Format validation (regex), normalization (strip dashes/spaces) |
| `Email` | [member/models.py](../../../library/member/models.py) | Email format validation |
| `Password` | [member/models.py](../../../library/member/models.py) | Length validation (raw form before hashing); `__str__` hides value |

## Edge cases to remember

- **Tuple/multi-field VOs:** if VO has 2+ fields (e.g., `Money(amount, currency)`), all must be frozen + validated in `__post_init__`
- **Unicode + case:** `Email("ALICE@EXAMPLE.COM")` should equal `Email("alice@example.com")` after normalization
- **Trimming whitespace** is almost always the right call — but document if it isn't
- **Don't put I/O** in `__post_init__` — no DB lookup, no HTTP, no file reads

## Do not

- ❌ Use custom exception classes — raise `ValueError`
- ❌ Mutate fields after construction (`@dataclass(frozen=True)` enforces this; don't try with `object.__setattr__` anywhere except in `__post_init__`)
- ❌ Add behaviour methods exceeding 5 — at that point reconsider VO vs Entity vs domain service
- ❌ Put VOs in `ports.py`, `repositories.py`, or `api/` — they live in `models.py` with the entity
- ❌ Skip the frozen-ness test — it documents the invariant
