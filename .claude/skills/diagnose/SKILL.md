---
name: diagnose
description: Systematic methodology for debugging tough bugs and performance issues — build a feedback loop first, hypothesise with falsifiable predictions, instrument, fix at the right seam, post-mortem.
---

# Diagnose

When the human says "I have a bug" / "this test is failing intermittently" / "something is slow" / "X used to work and doesn't anymore":

Apply a structured 6-phase debug methodology. **Do not start guessing fixes.** Guesswork burns hours; methodology cuts to root cause.

## Core principle

> **If you have a fast, deterministic, agent-runnable pass/fail signal for the bug, you will find the cause. Everything else follows from this.**

Without a reliable reproducer, debugging is gambling. Spend most of the effort on the loop, then the cause falls out mechanically.

## The six phases

### Phase 1 — Build the feedback loop (most important)

Goal: a command that returns **PASS** when the bug is absent and **FAIL** when present, runs in **< 10 seconds**, and is **deterministic** (same result every time).

Techniques, in order of preference:

1. **Failing unit test** — `pytest tests/<slice>/<area>/test_<file>.py::test_<name>`
2. **Failing integration test** — slower but real interactions
3. **HTTP test via `httpx.AsyncClient` + `ASGITransport`** — for API bugs
4. **Standalone script** — `python -m library.<entry>` with specific input
5. **`curl` + running server** — last resort, slow
6. **Manual reproduction with checklist** — if nothing else works, write down the steps

**For non-deterministic bugs:** raise the reproduction rate to debuggable levels first:
- Loop the test 100 times: `pytest --count=100 <test>`
- Add timing noise: `pytest -p no:randomly` to control test order
- Use `pytest-asyncio` event loop debug mode
- Make the time/randomness deterministic via `FakeClock` / fixed seeds

**Be aggressive. Be creative. Refuse to give up on building the loop.** If you can't build one, STOP and surface to the human — don't hypothesise blindly.

### Phase 2 — Confirm the loop reproduces the right bug

Critical check: does your loop fail **for the same reason** the user reported?

```sh
pytest <your-loop> -v
```

Look at:
- **Failure message** — matches the user's symptom?
- **Stack trace** — points at code near the user's described issue?
- **Side effects** — did the bug also produce the user's observed side effect (wrong DB row, wrong email sent)?

If the loop fails for a **different reason** (e.g., your test setup is broken, not the production code), fix the test and re-confirm. Don't proceed until the loop **clearly** captures the user's bug.

### Phase 3 — Hypothesise (3–5 falsifiable predictions)

Before writing any debug code, generate **3 to 5 hypotheses** about the root cause. Each must be **falsifiable** — you can predict, "If X is the cause, then changing Y will make the bug disappear."

Template:

```
Hypothesis 1: <root cause guess>
  Falsifier: If I <change Y>, the loop will <pass / behave differently>.
  Confidence: <low / medium / high>

Hypothesis 2: ...
```

**Why 3–5:** one hypothesis = anchoring bias (you'll force-fit evidence). Too many = you're guessing. Three to five is the sweet spot.

**Examples for this codebase:**

```
Hypothesis 1: FakeClock isn't being injected in the failing test, so
  the use case is calling datetime.now() and reading the real clock.
  Falsifier: If I add an explicit clock=FakeClock(...) argument and
  re-run, the test passes.

Hypothesis 2: The contract test for sql_repository is hitting
  connection-pool exhaustion when running in parallel with cache tests.
  Falsifier: If I add @pytest.mark.serial to the SQL tests and re-run,
  the failures disappear.

Hypothesis 3: A new dependency upgrade changed JWT signature behaviour.
  Falsifier: If I `pip install jwt==<previous>` and re-run, the test passes.
```

**Share hypotheses with the human** before testing — they may rule some out from domain knowledge ("no, that path doesn't run in this scenario").

### Phase 4 — Instrument

For each hypothesis, plant a **targeted probe** that will confirm or refute it. Cheap probes first.

Preferred tools, in order:

1. **`pdb.set_trace()` or `breakpoint()`** in the suspect line — interactive, deterministic
2. **`logger.info()` with `extra={...}`** for structured context — uses the project's structlog setup
3. **`print(f"DEBUG <where>: <var>={var}")`** for quick one-offs — tag with `DEBUG <where>` so you can grep them out later
4. **`pytest --pdb`** to drop into debugger on failure
5. **`pytest -s`** to see stdout during tests
6. **Differential test** — copy the failing test, vary one input, see what changes

**Rules:**
- **One probe per hypothesis.** Blanket logging makes the output unreadable.
- **Tag probes** so you can find and remove them later (e.g., `# DEBUG-1234 remove before commit`).
- **Don't commit probes.** They get cleaned up in Phase 6.
- **Prefer debugger** over print-debugging when feasible — you get the whole state, not just the variable you remembered to print.

Run the loop with each probe, observe, refute or confirm.

### Phase 5 — Fix + regression test

Once you know the cause, **the fix is usually obvious**. The discipline:

1. **Write the regression test first** — at the architectural seam where the bug actually lives.
   - Bug in domain logic? → unit test in `tests/<slice>/domain/`
   - Bug in use case orchestration? → application test with fake repos
   - Bug in repository? → contract test or impl-specific test
   - Bug at the HTTP boundary? → API test with httpx client
   - Bug in config? → test in `tests/shared/test_config.py`
2. **Run the regression test — confirm it fails** for the right reason
3. **Apply the fix**
4. **Run the regression test — confirm it passes**
5. **Run the full suite** (`pytest -W error`) — confirm nothing else broke

**Place the test at the right seam.** A bug in `OrderTotal` math shouldn't be regression-tested via an HTTP endpoint test — that's too coarse. Test at the layer that owns the bug.

### Phase 6 — Cleanup + post-mortem

1. **Remove debug probes** — search for `DEBUG`, `print(`, `breakpoint()`. Verify zero.
2. **Run `/verify`** — full suite green.
3. **Commit** via [`/git-commit`](../git-commit/SKILL.md). Subject: `fix(<scope>): <one-line cause>`. Body explains **root cause** and **why the fix works**.
4. **Post-mortem in commit body or `.scratch/`:**
   - What was the cause? (one sentence)
   - Why did the existing tests miss it? (gap in coverage / gap in test design)
   - What systemic prevention is possible? (e.g., "add a property-based test", "enforce in CI", "tighten the type signature")

Example post-mortem commit:

```
fix(loan): prevent double-borrow on concurrent requests

Root cause: BorrowBookUseCase checks book.available, then saves the
loan, but these were not in a single transaction. Two concurrent
requests both passed the check before either committed.

Fix: wrap the read-then-write in book_repo.try_borrow(book_id) at
the repository level, atomic per backend (SELECT FOR UPDATE in SQL).

Why tests missed it: integration test ran requests sequentially.
Added test that fires two BorrowBookUseCase.execute() concurrently
via asyncio.gather and asserts exactly one succeeds.

Co-Authored-By: Claude <noreply@anthropic.com>
```

## Anti-patterns

| Anti-pattern | Fix |
|---|---|
| "I'll just try a fix and see if it works" | Build the loop first. No loop = no debug. |
| One blanket `print()` everywhere | One probe per hypothesis. Targeted. |
| Hypothesising without a falsifier | If you can't predict, you can't verify. Rephrase. |
| Fixing the test instead of the code (when the test was right) | If the test was correct, fix the code. Don't muzzle the test. |
| Skipping the regression test ("the fix is obvious") | The regression test prevents the same bug recurring next quarter. |
| Committing with debug probes still in | Cleanup is part of the process. |
| Treating a deprecation warning as the cause when it's a symptom | Look at the actual failure, not the noise around it. |

## Project-specific debug tools you have

This codebase makes debugging **much easier** than a typical project:

- **`FakeClock(fixed_now=...)`** — eliminates time as a variable
- **SQLite `:memory:` (one engine per test)** — eliminates the production DB as a variable; fast enough that `metadata.create_all` per test is invisible
- **`fakeredis`** — eliminates Redis as a variable
- **`FakePasswordHasher`** — eliminates Argon2 cost as a variable
- **Parametrized contract tests** — bug only in raw SQL? in the cached wrapper? in the Redis variant? The fixture parameter tells you immediately.
- **`structlog` with `contextvars`** — every log line carries `request_id`, so you can grep one request's full trace
- **`pytest -W error`** — surfaces deprecation warnings before they become bugs
- **Type hints + `mypy` (strict)** — many "bugs" are actually type mismatches caught at type-check; ruff catches the static-analysis subset

**Leverage these before reaching for live debugging.** If `pytest tests/<slice>/domain/` passes but `pytest tests/<slice>/application/` fails, the bug is in orchestration — narrow scope by 90% immediately.

## When to stop and ask the human

- ⏸ **Can't build a deterministic loop** after reasonable effort — surface what you tried and what blocked it
- ⏸ **All 3–5 hypotheses refuted** — you may be looking in the wrong place; share what you ruled out and ask for context
- ⏸ **Fix touches more than 2 slices** — likely a deeper architectural issue, not a bug
- ⏸ **Bug is in a third-party library** — confirm with human before patching or pinning
- ⏸ **Production data corruption suspected** — don't run any fix script without explicit OK

## Resume one-liner

> **6 phases: (1) build fast deterministic loop, (2) confirm it captures the user's bug, (3) hypothesise 3–5 falsifiable causes, (4) instrument one probe per hypothesis, (5) regression test at the right seam + fix, (6) cleanup + post-mortem. The loop is most of the work; everything else is mechanical from there. This codebase's fakes (FakeClock, in-memory repos, fakeredis) make Phase 1 cheap — use them.**
