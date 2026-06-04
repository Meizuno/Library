---
name: verify
description: Run the full pre-commit verification — tests, lint, spellcheck, security — and report any failures.
---

# Verify

Run the full pre-commit verification suite for this project. **Do this before declaring work done.** This is the same set CI runs on every push.

## What to run

Execute in this order, **stop on first failure**:

### 1. Tests (warnings = failures)

```sh
pytest -W error
```

Expected: **405 passed, 0 warnings**. If a deprecation warning appears, fix it — do NOT silence it with `-W ignore::DeprecationWarning`.

### 2. Linter — must score 10.00/10

```sh
pylint library tests
```

Expected: `Your code has been rated at 10.00/10`. If lower, fix the underlying issue. Do **not** add `# pylint: disable=...` to silence. Acceptable global disables are already in [`pyproject.toml`](../../../pyproject.toml) under `[tool.pylint."messages control"]`.

### 3. Type checker — must be clean

```sh
mypy library tests
```

Expected: `Success: no issues found in 150 source files`. mypy is configured `strict = true` in [`pyproject.toml`](../../../pyproject.toml) under `[tool.mypy]`, with a slightly loosened override for `tests.*` that skips the "missing return annotation on every test function" noise but keeps real correctness signals (union-attr, no-any-return, attr-defined, call-arg). Do **not** add `# type: ignore[...]` to silence — fix the underlying type. Acceptable per-line ignores already in the tree carry a comment explaining why (SQLAlchemy `result.rowcount` on `Result[Any]`, structlog's untyped `BoundLoggerLazyProxy`, deliberately-wrong test inputs around `pytest.raises`).

### 4. Spellcheck

```sh
codespell --skip="*.lock,.git,__pycache__,.venv,*.egg-info,.pytest_cache,.claude"
```

Expected: zero hits. If there's a false positive (technical term), add it to a project codespell ignore list — do NOT comment it out per-line.

### 5. Bandit — code-level security

```sh
bandit -r library
```

Expected: no Medium or High severity findings. Low-severity findings (like `B101: assert_used`) in tests are typically fine.

### 6. pip-audit — dependency CVEs

```sh
pip-audit --skip-editable
```

Expected: no known vulnerabilities in declared dependencies.

### 7. License audit — no GPL-family

```sh
pip-licenses --fail-on="GPL;LGPL;AGPL"
```

Expected: pass. The project intentionally uses only permissively-licensed dependencies.

## Report format

After running all seven, report to the human:

```
✅ pytest:      405/405 passed, 0 warnings
✅ pylint:      10.00/10
✅ mypy:        no issues found
✅ codespell:   clean
✅ bandit:      no medium/high findings
✅ pip-audit:   no vulnerabilities
✅ pip-licenses: no GPL-family dependencies
```

If something failed:

```
❌ pytest: 2 failures in tests/loan/application/test_borrow_book.py
   - test_borrow_already_borrowed_book: AssertionError ...
   - test_borrow_unverified_member: missing fixture 'verified_member'

⏭️ pylint: skipped (pytest failed)
⏭️ ...
```

Then **fix the failures** before continuing. Do not suggest "ignoring" or "skipping" them.

## When to run

- ✅ Before committing
- ✅ After generating new code with `/add-use-case`, `/add-slice`, `/add-repository-impl`, `/add-value-object`
- ✅ Before declaring a task complete
- ✅ After resolving a merge / rebase
- ✅ When the human asks "is everything green?"

## Common failures and fixes

### `pytest -W error` fails on a deprecation warning

Fix the deprecated usage. Common culprits:
- `datetime.utcnow()` → `datetime.now(timezone.utc)`
- `pkg_resources` → `importlib.metadata`
- `pytest.warns()` without `match=...` argument

### `pylint` scores below 10.00

Read the report. Common fixes:
- `unused-import` — remove the import
- `too-many-locals` (refactor) — extract a helper function
- `too-many-arguments` (refactor) — accept a dataclass instead of many params
- `inconsistent-return-statements` — make all branches return same type

If a warning is clearly a false positive (e.g., `protected-access` inside the class's own test), use `# pylint: disable=<rule>` **only on the specific line** with a comment explaining why.

### `codespell` hits a domain term

Add to the project's codespell allow list. Don't ignore inline.

### `bandit` flags an assert in production code

Convert to explicit `raise AssertionError(...)`. Bandit flags `assert` because Python optimizer strips it with `-O`.

### `pip-audit` finds a vulnerability

- If the affected library is in `dependencies`: bump version in `pyproject.toml`
- If transitive: bump the parent dependency
- If no fix available yet: confirm with human whether to wait or pin to last safe version

### `pip-licenses` finds a GPL dependency

- Check if it's transitive — sometimes you can switch the parent dep
- If direct — replace with a permissively-licensed equivalent
- This project intentionally avoids GPL family

## Do not

- ❌ Skip any of the 7 checks
- ❌ Add `# pylint: disable=...` or `# type: ignore[...]` to silence a warning rather than fixing it
- ❌ Add `-W ignore` to pytest to mask warnings
- ❌ Declare a task done with any check failing
- ❌ Run only the first check that passes and call it good — the suite is a chain
