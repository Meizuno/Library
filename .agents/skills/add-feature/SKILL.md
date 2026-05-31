---
name: add-feature
description: Orchestrate a feature end-to-end as small vertical slices, each on its own branch with atomic commits. Delegates code generation to other skills.
---

# Add Feature

When the human describes a **multi-step feature** (e.g., "add reminder notifications for due loans", "add password reset flow", "support OAuth login"):

This is a **meta-skill** that orchestrates:
- Feature decomposition into vertical slices
- One branch per slice (`feat/<slice-name>`)
- Delegation to code-gen skills ([`/add-use-case`](../add-use-case/SKILL.md), [`/add-slice`](../add-slice/SKILL.md), [`/add-value-object`](../add-value-object/SKILL.md), [`/add-repository-impl`](../add-repository-impl/SKILL.md))
- [`/verify`](../verify/SKILL.md) + [`/git-commit`](../git-commit/SKILL.md) between slices
- Branch lifecycle (create, commit, merge, switch to next)
- [`/handoff`](../handoff/SKILL.md) at the end

**Do not** generate code directly in this skill. Always delegate to the appropriate sub-skill.

## Workflow

### Step 1 — Understand the feature

Ask the human (concise — 2–3 questions max):

- What user-visible behaviour are you adding? (one sentence)
- What triggers it? (HTTP request? scheduled task? domain event? CLI?)
- What slice(s) does it touch? — book / member / loan / auth / notification / shared / new
- Does it need new persistence (new table / new repository)? new VO? new external integration?

Confirm understanding in **one sentence** before proceeding:
> "OK — adding `<feature>` that triggers on `<event>`, touching `<slices>`, persisting `<entity>` via SQL. Right?"

Wait for confirmation. Do not assume.

### Step 2 — Decompose into vertical slices

Read [AGENTS.md](../../../AGENTS.md) to remember the slice structure.

Propose a **slice list** as a numbered plan. Each slice must be:
- **End-to-end through layers** (domain → application → infrastructure where touched)
- **Self-contained** — its tests pass independently
- **30–90 minutes** of work
- **Independently mergeable** to main

**Standard decomposition order:**

```
1. Port + InMemory impl + test    ← foundation, no business logic yet
2. SQL impl + contract test       ← persistence (skip if no DB involved)
3. Use case + application tests   ← business logic, using fakes
4. Composition root wiring        ← DI in shared/presentation/api/dependencies.py
5. Presentation layer + API tests ← HTTP endpoint
6. Cron / scheduler entry point   ← if scheduled (else skip)
7. Docker / CI tweaks             ← only if infra needs changes
8. README / docs update           ← architectural choices worth recording
```

Not every feature has all 8. Most have 3–5.

**Example for "reminder notifications":**

```
Slice 1: NotificationLog port + InMemory impl + test
         Branch: feat/notification-log-port
Slice 2: SQL NotificationLog impl + contract test
         Branch: feat/notification-log-sql
Slice 3: CheckDueLoansUseCase for due-in-3 reminders + tests
         Branch: feat/check-due-loans-use-case
Slice 4: Wire CheckDueLoansUseCase in composition root
         Branch: feat/wire-due-loans-check
Slice 5: APScheduler / cron entry point
         Branch: feat/due-loans-scheduler
Slice 6: Add due-in-1 + overdue reminder types
         Branch: feat/multiple-reminder-types
Slice 7: README + docker-compose updates
         Branch: docs/notification-reminders
```

Show this plan to the human. **Wait for approval.** The human may merge slices, reorder, or split further.

### Step 3 — Implement slice-by-slice

For **each** slice in the approved plan, execute this cycle:

#### 3.1 — Create the branch

Use [branches.md](../git-commit/branches.md). Standard flow:

```sh
git switch main
git pull --ff-only origin main
git switch -c <type>/<slice-name>
```

If the previous slice's branch has uncommitted work, **stop and resolve** — don't carry mess across branches.

#### 3.2 — Generate the code

**Pick the right sub-skill** based on what the slice produces:

| Slice produces | Sub-skill |
|---|---|
| New bounded-context slice (folder + skeleton) | [`/add-slice`](../add-slice/SKILL.md) |
| New use case in existing slice | [`/add-use-case`](../add-use-case/SKILL.md) |
| New Value Object | [`/add-value-object`](../add-value-object/SKILL.md) |
| New repository backend | [`/add-repository-impl`](../add-repository-impl/SKILL.md) |
| Composition-root wiring only | Hand-edit [`shared/presentation/api/dependencies.py`](../../../library/shared/presentation/api/dependencies.py) |
| Cron / scheduler entry point | Hand-write (no skill yet) |
| README / docs | Hand-write |

Tell the human which sub-skill you're using: "Invoking `/add-value-object` to create `NotificationKind`."

#### 3.3 — Verify

After the slice's code is written:

```sh
/verify
```

(Or at minimum `pytest -W error && pylint library tests`.)

If verification fails — **fix it on this branch**. Do not commit broken code, do not move to the next slice.

#### 3.4 — Commit

```sh
/git-commit
```

The skill handles the message and the commit. The branch you created in 3.1 is already in the right place.

**Most slices = exactly one commit.** If a slice is large enough to need 2–3 commits (e.g., "add port" + "add impl" + "add wiring"), do them as separate atomic commits within the same branch — each green on its own.

#### 3.5 — Decide: merge now or continue?

Surface options to the human:

> "Slice 1 done. Options:
> 1. Merge to main now (squash or fast-forward) — clean checkpoint
> 2. Push to remote without merging — for review
> 3. Continue directly to slice 2 (next branch) — accumulate commits, merge later"

**Default — stay on the branch.** Do not merge automatically. The human decides cadence.

If continuing:

```sh
# back to main first (if previous slice merged)
git switch main && git pull --ff-only

# OR: branch from current head if next slice depends on previous
# (rare — most slices are independent)

git switch -c <type>/<next-slice-name>
```

### Step 4 — Pause and re-plan after every 2–3 slices

Long feature plans (8+ slices) tend to drift. After ~3 slices, **stop and ask**:

> "Done with slices 1–3. Anything we learned that changes the rest of the plan?
> - Slice 5 (`<scheduler>`) — still needed as designed?
> - Slice 7 (`<docker tweaks>`) — turned out unnecessary?
> - New slice we didn't plan?"

Update the plan, then continue.

### Step 5 — Final cleanup

After **all slices** are merged to main:

1. `git switch main && git pull --ff-only`
2. Delete merged feature branches:
   ```sh
   git branch --merged main | grep -v 'main' | xargs git branch -d
   git fetch --prune                  # clean up deleted remote-tracking
   ```
3. Run [`/verify`](../verify/SKILL.md) on main — confirm green
4. Run [`/handoff`](../handoff/SKILL.md) — record:
   - The feature delivered (one line)
   - Slices completed (numbered)
   - Decisions made and **why**
   - Open follow-ups (TODOs, refactors postponed)

## Decision points where you must ask the human

This skill is **interactive**. Do not silently proceed past:

- ⏸ **Slice plan** before starting any branch
- ⏸ **Branch creation** — show the branch name, confirm
- ⏸ **Merge to main** — never automatic
- ⏸ **Push to remote** — explicit ask
- ⏸ **PR creation** — explicit ask
- ⏸ **Unexpected verification failures** that need design choice
- ⏸ **Re-planning** every 2–3 slices

## Anti-patterns this skill prevents

| If you find yourself... | The skill says |
|---|---|
| Generating files for 6 different slices in one go | Stop. One slice at a time, one branch at a time. |
| Committing on `main` directly | Stop. Branch first. |
| Writing one giant commit at the end of the feature | Stop. Commit per slice. |
| Skipping `/verify` because "it's just the next slice" | Stop. Verify every slice. |
| Merging slice 3 without finishing slice 2's tests | Stop. Each slice is independently green. |
| Letting branches accumulate (5 open branches for 1 feature) | Stop. Merge or close before continuing. |

## Reference flow

```
human: "add reminder notifications for due loans"

agent:
  1. Asks 2–3 clarifying questions
  2. Proposes 7 slices
  3. Human approves

For slice 1 (NotificationLog port):
  → git switch -c feat/notification-log-port
  → invoke /add-value-object for NotificationKind
  → invoke /add-repository-impl style (with new InMemory only)
  → /verify
  → /git-commit
  → "Slice 1 done. Merge now or continue?"
```

## Hard rules

- ❌ Never generate code for the entire feature at once — always slice-by-slice
- ❌ Never commit on `main` — always on a feature branch
- ❌ Never merge automatically — surface the option, let the human decide
- ❌ Never skip `/verify` between slices
- ❌ Never accumulate multiple uncommitted slices on one branch — commit per slice
- ❌ Never push or open a PR without the human asking

## Resume one-liner

> **One feature = many slices. One slice = one branch. One branch = atomic commit(s) + green tests + ready to merge. The skill orchestrates: decompose, then for each slice — branch, generate (via sub-skill), verify, commit, decide. Stop and ask between slices; never auto-merge.**
