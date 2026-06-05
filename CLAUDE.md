# CLAUDE.md

## Authoritative instructions

The source of truth for architecture, coding standards, testing, and forbidden patterns is **[AGENTS.md](AGENTS.md)**. Read it first.

For setup, motivation, and detailed architectural rationale, see **[README.md](README.md)**.

---

## Quick orientation

This is a Python 3.12+ async backend (FastAPI + SQLAlchemy 2.x Core + Postgres + Redis), structured as a **modular monolith** with **flat per-module layout** (`book/`, `member/`, `loan/`, `auth/`, `notification/`, `shared/`). Each module's dependency rule is encoded by file (`models.py` → `ports.py` → `repositories.py` / `use_cases/` / `api/`), not by directory. Side-effects on domain transitions go through an in-process event bus ([`EventPublisher`](library/shared/ports.py) → [`InProcessEventBus`](library/shared/adapters.py) → `<consumer>/subscribers.py`), not direct calls. 415 tests guard every architectural claim.

Before touching code:

```sh
pytest -W error               # must pass clean — warnings are failures
ruff check library tests      # must report "All checks passed!"
mypy library tests            # must report "no issues found"
```

Or just run [`/verify`](.claude/skills/verify/SKILL.md), which mirrors CI step-for-step.

---

## Claude-specific preferences

### Voice & tone

- Lean on the codebase's actual patterns (Repository, Clock port, Use Cases as classes) when answering — anchor advice in real files, not generic textbook DDD.
- Keep replies focused; reference [AGENTS.md](AGENTS.md) sections instead of re-explaining them.
- Code, identifiers, comments, commit messages — always English. (Enforced by ruff's RUF001/002/003.)

### Editing discipline

- **Read the file before editing.** This codebase has been refactored several times; the README and folder layout are the source of current truth, not memory of past sessions.
- **Prefer surgical edits** over rewrites. The architecture is stable — most tasks are "add a use case to module X" or "wire a new adapter".
- **Mirror existing patterns.** New use case → look at [`AddBookUseCase`](library/book/use_cases/add_book.py). New repository → look at [`SqlBookRepository`](library/book/repositories.py). New VO → look at [`ISBN`](library/book/models.py).
- **Mirror tests.** Tests live under `tests/<module>/{test_models.py, repositories/, use_cases/, api/}`. New use case file → new test file at `tests/<module>/use_cases/test_<verb>_<noun>.py`.

### When the human asks for a feature

- A feature usually means a **new use case** in an existing module, or a **new module** entirely.
- Match the flat layout: `models.py` (entities + VOs), `ports.py` (Protocols), `exceptions.py` (DomainError + ApplicationError split), `repositories.py` (all port impls + the SQLAlchemy table), `use_cases/<verb>_<noun>.py` (Command + UseCase together), `api/dependencies.py` + `api/schemas.py` + `api/routes/<verb>_<entity>.py`.
- Feature-private DI providers live in `<module>/api/dependencies.py`. Cross-module port wiring (e.g., `auth.ports.CredentialVerifier` bridged to `member.repositories.MemberCredentialVerifier`) goes in [`shared/api/dependencies.py`](library/shared/api/dependencies.py) — the composition root.
- Add tests at every layer that has logic. Skip layers that are trivial pass-through.

### When the human asks an architectural question

- Anchor answers in this codebase's actual decisions ("the README explicitly chose X over Y because…"), not generic textbook DDD/Clean Architecture.
- The "What this project deliberately does NOT do" section of [AGENTS.md](AGENTS.md) is the catalog of conscious omissions. Reference it before suggesting CQRS, event sourcing, UoW, etc.

### Don't

- Don't propose Domain Event Bus, CQRS, Event Sourcing, RBAC, Unit of Work, or generic `BaseEntity` without confirming — these were considered and intentionally rejected.
- Don't generate code that violates the Dependency Rule. File-level layer violations (`use_cases/*.py` importing `repositories.py`, `models.py` importing Pydantic, etc.) are immediate fails.
- Don't add `# noqa: ...` or `# type: ignore[...]` to silence warnings. Fix the underlying issue. The few legitimate ones in the tree all carry an inline rationale comment.
- Don't introduce new third-party dependencies without confirming.
- Don't reintroduce the deep `domain/` / `application/` / `infrastructure/` / `presentation/` layer-folder layout. The flat per-module shape is deliberate.

### Git workflow

The human owns the gates. Make edits freely; never cross a workflow gate without explicit invocation.

- **Before starting work on a new feature or refactor**: list existing branches (`git branch -vv && git branch -r`). If a branch already exists for this scope (by name, recent commits, or what the human says they're working on), **propose reusing it** before suggesting a new one. Avoid branch proliferation — the human prefers one branch per logical chunk of work, reused when possible.
- **Don't commit automatically.** Commits happen only when the human invokes [`/git-commit`](.claude/skills/git-commit/SKILL.md) or says "commit" / "commit it". Edits-without-commit is a valid resting state — let the human gate the commit. After making changes, surface what changed and **stop**; do not run `git commit` inline.
- **Don't push automatically.** Pushes happen only when the human invokes [`/git-push`](.claude/skills/git-push/SKILL.md) or says "push" / "push it". `/git-commit` ends on a local commit; pushing is a separate, explicit step.
- **Don't merge to main locally.** Merges happen on GitHub via PR. The human reviews, merges, and GitHub auto-deletes the source branch. Locally, [`/git-sync`](.claude/skills/git-sync/SKILL.md) handles cleanup (fetch + prune + safe-delete merged local branches).

---

## Tooling notes

- The repo uses `uv` for dependency resolution (`uv.lock` is checked in) but `pip install -e ".[dev]"` works equally well in CI.
- Tests use `pytest-asyncio` in `auto` mode — async tests don't need decorators.
- Logs use `structlog` with `contextvars.merge_contextvars` — every log line in a request automatically carries `request_id`, `method`, `path`. Don't manually thread these through.
- Lint = ruff (covers pylint's value + bandit's `S` security rules + import sorting + pyupgrade + pytest-style). Pylint and bandit were removed.
- Type-check = mypy strict, with a loosened `tests.*` override that skips "every function needs `-> None`" noise but keeps real correctness signals (union-attr, no-any-return, attr-defined, call-arg, misc).
