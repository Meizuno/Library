---
name: handoff
description: Generate a session summary so the next AI session (or human) can pick up exactly where this one left off.
---

# Handoff

When the human says "handoff" / "summarize what we did" / "I'll come back to this later":

Produce a **markdown summary** that lets a fresh AI session (or future-you) resume the work without re-reading the entire transcript.

## Output location

Write the file to:

```
.scratch/handoff-YYYY-MM-DD-HHMM.md
```

(Create `.scratch/` if it doesn't exist. Check `.gitignore` — if `.scratch/` is not ignored, ask the human whether to commit or add to `.gitignore`.)

## Output format

```markdown
# Handoff — <topic in one line>

**Date:** YYYY-MM-DD HH:MM
**Session goal:** <what was the human trying to achieve?>

## What was done

- <Bullet of concrete change — file path + 1-line description>
- <Bullet>
- <Bullet>

## What's pending

- [ ] <Concrete next step, with file path if known>
- [ ] <Concrete next step>
- [ ] <Concrete next step>

## Key decisions made

- **<Decision name>:** <One-line summary>. Reasoning: <one line>.
- **<Decision name>:** ...

## Key files touched

- `library/<slice>/...` — <what changed and why>
- `tests/<slice>/...` — <what was added>
- `pyproject.toml` — <if relevant>

## Tests / verify status

- `pytest -W error`: <pass / N failing — list them>
- `ruff check library tests`: <pass/fail>
- `mypy library tests`: <pass/fail>
- (skip others if not relevant)

## Open questions for the human

- <Question 1>
- <Question 2>

## To resume in next session

1. <First concrete action>
2. <Second concrete action>
3. Re-run `/verify`
```

## What to include

- **Concrete file paths and line ranges** where applicable (`library/loan/application/use_cases/borrow_book.py:42-58`)
- **Decisions** with reasoning, not just outcomes ("Chose closure DI over class-based because X")
- **Open questions** that blocked progress
- **Exact next action** — not "continue working on loans" but "add `cancel_loan` use case in `library/loan/application/use_cases/cancel_loan.py`, mirroring the shape of `borrow_book.py`"

## What to skip

- Conversational chatter ("the user said `далі` 5 times")
- Re-explanations of the codebase (the next agent has AGENTS.md)
- Code blocks longer than 10 lines — link to the file instead
- Things already in git history (commit messages cover that)

## Tone

- Direct and operational, like a flight log
- Past tense for done, future tense for pending
- One sentence per bullet — no paragraphs

## Reference structure

A good handoff is the document a tired developer reads on Monday morning and immediately knows what to do. A bad handoff is a wall of text recapping the whole week.

Length target: **80–250 words**. If you're writing more, you're explaining instead of summarizing.

## After writing

After writing the handoff file, read it back and verify:

- [ ] **One-line topic** captures the goal
- [ ] Each "What was done" item references a real file
- [ ] Each "Pending" item is **concrete** (file path + action)
- [ ] "Resume in next session" gives a fresh agent a first move
- [ ] No prose paragraphs — everything is bullets or tables

Tell the human: "Handoff saved to `.scratch/handoff-YYYY-MM-DD-HHMM.md`."

## Do not

- ❌ Include the full conversation transcript
- ❌ Re-explain architecture (AGENTS.md does that)
- ❌ Write prose paragraphs — bullets only
- ❌ Use vague pending items ("finish the auth thing") — be specific
- ❌ Forget the "Resume in next session" — that's the most-read section
