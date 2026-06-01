---
name: update-readme
description: Sync auto-derivable sections of README.md (project layout, HTTP API table, tech stack, test count, slice list) with the current state of the code.
---

# Update README

When the human says "update the readme" / "the readme is out of date" / after adding a slice / after adding endpoints / after dependency bumps:

Re-sync the **machine-derivable** sections of [`README.md`](../../../README.md) with the current code. Leave **human-written prose** (philosophy, architectural decisions, "what this project deliberately does not do") **untouched**.

## Sections this skill maintains

| README section | Source of truth | How to re-derive |
|---|---|---|
| **Project layout** (folder tree) | `library/` directory structure | `find library -type d -not -path '*__pycache__*'` |
| **HTTP API** (endpoint table) | All `*/presentation/api/router.py` files | grep / read routers |
| **Tech stack** (library list) | `pyproject.toml` `dependencies` | parse `[project]` and `[project.optional-dependencies]` |
| **Test count** ("N tests") | actual test suite | `pytest --collect-only -q | tail -1` |
| **Pylint score** ("10.00/10") | actual pylint run | `pylint library tests | tail -2` |
| **Bounded contexts list** | top-level folders in `library/` | inspect `library/*/` |
| **Required env vars** | `shared/config.py` `Settings` class | parse Pydantic model |

## Sections this skill does **NOT** touch

These are human-curated and must not be auto-rewritten:

- 📌 "The Dependency Rule, made concrete" — architectural philosophy
- 📌 "Core patterns demonstrated" — explanation of each pattern
- 📌 "Architectural decisions worth highlighting" — rationale
- 📌 "What this project deliberately does NOT do" — intentional omissions
- 📌 "Auth & email verification" lifecycle diagram — domain narrative

If the human asks to change one of these, treat as a regular Edit — not a skill task.

## Workflow

### Step 1 — Inspect current state

Run in parallel:

```sh
find library -type d -not -path '*__pycache__*' -not -path '*.egg-info*' | sort
ls library/                                                                    # top-level slices
pytest --collect-only -q 2>/dev/null | tail -3                                # test count
```

Read `pyproject.toml` for dependencies. Read each `library/*/presentation/api/router.py` to enumerate endpoints.

### Step 2 — Compare with README

Read [`README.md`](../../../README.md). For each maintained section, compute the **diff** between current code and what the README says:

- New slices not listed in "Project layout" tree
- New endpoints not in the HTTP API table
- Dependencies in `pyproject.toml` not mentioned in "Tech stack"
- Test count number that's now stale
- Bounded contexts mentioned in README but no longer existing

**Show the diff to the human before editing.** Format:

```
README updates needed:

[Project layout]
  + library/reservation/  (new slice not in README)
  - library/cli/          (removed slice still in README)

[HTTP API]
  + POST /reservations              (new endpoint)
  + DELETE /reservations/{id}       (new endpoint)
  - POST /loans/legacy              (removed endpoint still in README)

[Tech stack]
  + aiosmtplib                      (in pyproject, not in README)
  + pyjwt                            (in pyproject, not in README)

[Test count]
  README says: "396 tests"
  Actual:      "417 tests"

[Required env vars]
  + APP_BASE_URL  (new in config.py, not documented)
  + SMTP_*        (new in config.py, not documented)
```

Wait for confirmation before editing.

### Step 3 — Update each section in place

Use `Edit` tool with `old_string` / `new_string` for surgical updates. **Do not rewrite the README**. One Edit call per section so the human can review per-section.

#### Project layout tree

Replace the existing tree with the regenerated one. Preserve:
- The inline comments that explain folder purposes (`# Book (entity, with description)`)
- The trailing context after the tree

If you add a new slice, give it the same comment style as existing entries:

```
├── reservation/                  # Bounded context: reservations
│   ├── domain/
│   ├── application/
│   ├── infrastructure/
│   └── presentation/api/
```

#### HTTP API table

For each router, extract:
- HTTP method (`@router.get`, `@router.post`, etc.)
- Path (the decorator's first arg)
- Whether `Depends(get_verified_member)` is in the signature → "Bearer + verified"
- The function's `status_code=` kwarg or default

Update the table; keep the formatting `| Method | Path | Auth | Purpose |`. The **Purpose** column is human-written — preserve it for existing rows, and propose new rows but ask for the Purpose text.

#### Tech stack

Compare `pyproject.toml` dependencies (both required and `[dev]` and `[cli]`) against the README bullet list. Add new entries with **a one-line role** (e.g., `- aiosmtplib — async SMTP for the email notifier`). Don't auto-write the role — propose it, let the human edit if needed.

#### Test count

```sh
pytest --collect-only -q 2>/dev/null | tail -1
```

Look for "N tests collected" or similar. Update the `> N tests.` line at the top and the test-pyramid table totals at the bottom.

#### Bounded contexts list

If a new slice was added, surface it in:
- The "Project layout" intro paragraph: `"sliced by bounded context at the top level (book/, member/, loan/, auth/, notification/, <new>/)"`
- The "Cross-slice imports" subsection — if the new slice consumes/provides ports, document the direction

#### Required env vars in "Configure" section

Parse `shared/config.py` `Settings` fields. For each new field with no default (required) or interesting Literal, add to the `.env` example block.

### Step 4 — Pre-flight check

Before saving the updated README:

1. **Markdown lint** — run `mdl` or visually scan for broken table syntax
2. **Link check** — every `[text](path)` reference must point to an existing file
3. **Tree validity** — folder tree matches `find library -type d` output
4. **No accidental deletions** — diff the before/after with `git diff README.md`, confirm only intended changes

### Step 5 — Commit

Invoke [`/git-commit`](../git-commit/SKILL.md) with `docs(readme)` scope:

```
docs(readme): sync project layout and HTTP API table

- Add reservation/ slice (created in feat/reservation-bc)
- Add POST /reservations and DELETE /reservations/{id} endpoints
- Update test count: 396 → 417
- Document APP_BASE_URL and SMTP_* env vars

Co-Authored-By: Claude <noreply@anthropic.com>
```

## When the skill **should NOT** auto-update

- ❌ A section's narrative is fundamentally different — surface and ask
- ❌ A new slice has no clear "purpose" comment — propose, don't assume
- ❌ An endpoint's "Purpose" column would be auto-generated nonsense ("Endpoint handler for POST /reservations") — ask the human for a description
- ❌ Removing something from README that's still referenced elsewhere (broken links)

When in doubt, **surface the diff to the human and stop**.

## Useful one-liners

```sh
# Folder tree
find library -type d -not -path '*__pycache__*' -not -path '*.egg-info*' | sort

# All API routes (from FastAPI routers)
grep -rE "@router\.(get|post|put|patch|delete)" library/*/presentation/api/router.py

# Dependencies from pyproject
python -c "import tomllib; print('\n'.join(tomllib.load(open('pyproject.toml', 'rb'))['project']['dependencies']))"

# Test count
pytest --collect-only -q 2>/dev/null | tail -1

# Pylint score
pylint library tests 2>/dev/null | tail -2

# Required env vars (no default)
grep -nE "^\s+\w+: \w+( = Field)?" library/shared/config.py
```

## Anti-patterns

| Pattern | Why wrong | Fix |
|---|---|---|
| Auto-rewriting the philosophical sections | Human-curated narrative gets destroyed | Touch only the table sections listed above |
| Updating without showing diff | Human can't review what changed | Always preview before Edit |
| Rewriting whole README in one Write | Loses git diff granularity | One `Edit` call per section |
| Adding endpoints without "Purpose" column | Reads like generated boilerplate | Ask the human for one line per new endpoint |
| Auto-deleting sections referenced elsewhere | Broken anchors / links | Cross-check before deleting |

## Resume one-liner

> **Re-syncs README's machine-derivable sections (project layout tree, HTTP API table, tech stack, test count, env vars, slice list) with the actual code state. Inspect → diff → confirm with human → surgical `Edit` per section → commit via `/git-commit` with `docs(readme)` scope. Leaves architecture philosophy, decision rationale, and "deliberately does not do" sections alone.**
