# `.agents/skills/`

Project-local AI skills. Each subfolder is a single skill with a `SKILL.md` (the main instruction file) and optional supporting files.

Skills are discovered automatically by Claude Code from the `.agents/skills/` directory. The human invokes a skill via a slash-command matching its name (e.g., `/add-use-case`).

## Available skills

Skills are physically flat in `.agents/skills/` (required for slash-command discovery), but **grouped by intent** below. Naming prefixes (`add-*` for code generation, `git-*` for version control) signal the group.

### 🎯 Orchestration

The entry point for multi-step features. Delegates to the leaf skills below.

| Skill | Purpose |
|---|---|
| [`/add-feature`](add-feature/SKILL.md) | Decompose a feature into vertical slices, one branch per slice, with verify + commit between |

### 🧱 Code generation (project-specific)

Generate code that matches this project's DDD + Hexagonal conventions. Each respects the Dependency Rule and the [`/verify`](verify/SKILL.md) gate.

| Skill | Purpose |
|---|---|
| [`/add-use-case`](add-use-case/SKILL.md) | Generate a new use case inside an existing bounded-context slice |
| [`/add-slice`](add-slice/SKILL.md) | Generate a full bounded-context slice skeleton (domain + application + infrastructure + presentation) |
| [`/add-value-object`](add-value-object/SKILL.md) | Generate a new Value Object with self-validation and tests |
| [`/add-port-adapter`](add-port-adapter/SKILL.md) | Add a new Port (Protocol) + Adapter pair, or a new Adapter for an existing Port (Logger, Notifier, PasswordHasher, …) |
| [`/add-repository-impl`](add-repository-impl/SKILL.md) | Add a new persistence backend (Mongo, file, etc.) for an existing repository protocol |

### 🌿 Version control

Branch-aware git workflow with Conventional Commits.

| Skill | Purpose |
|---|---|
| [`/git-commit`](git-commit/SKILL.md) | Conventional Commits message, branch detection / creation, verify, commit |
| └─ [`branches.md`](git-commit/branches.md) | (Supporting reference for `/git-commit`) Branch naming, switching, merging, PR conventions |
| [`/git-sync`](git-sync/SKILL.md) | Pull latest main, prune deleted remote refs, delete merged local branches, optional rebase |

### ✅ Quality

Run before every commit and before declaring work done.

| Skill | Purpose |
|---|---|
| [`/verify`](verify/SKILL.md) | Full pre-commit suite — pytest + pylint + codespell + bandit + pip-audit + pip-licenses |
| [`/diagnose`](diagnose/SKILL.md) | 6-phase debug methodology — build loop, hypothesise, instrument, fix at the right seam, post-mortem |

### 📚 Documentation

Keep the project's docs synced with the code.

| Skill | Purpose |
|---|---|
| [`/update-readme`](update-readme/SKILL.md) | Re-sync machine-derivable README sections (layout, API table, tech stack, test count, env vars) |

### 📋 Session

For working across multiple sessions or handing off to a teammate.

| Skill | Purpose |
|---|---|
| [`/handoff`](handoff/SKILL.md) | Generate a session summary to `.scratch/` for resuming later |

## How they compose

```
/add-feature                         ← orchestrator
   │
   ├──→ /add-slice                   ← per slice that needs new BC
   ├──→ /add-use-case                ← per slice that adds operation
   ├──→ /add-value-object            ← per slice that adds VO
   ├──→ /add-port-adapter            ← per slice that adds a Port + Adapter
   ├──→ /add-repository-impl         ← per slice that adds a new persistence backend
   │
   ├──→ /verify                      ← between slices
   ├──→ /diagnose                    ← when something breaks
   ├──→ /git-commit                  ← between slices (handles branch)
   │     └─ branches.md              ← supporting reference
   ├──→ /git-sync                    ← after merging a PR, before new slice
   ├──→ /update-readme               ← after slices / endpoints / deps change
   │
   └──→ /handoff                     ← at the end
```

**Single-step tasks** (add one use case, fix one bug) — invoke the leaf skill directly.
**Multi-slice features** — start with `/add-feature`.

## Naming conventions

Prefixes signal the group without subdirectories:

| Prefix | Group | Examples |
|---|---|---|
| `add-` | Code generation | `add-use-case`, `add-slice`, `add-value-object` |
| `add-<meta>` | Orchestrator (composes other `add-*`) | `add-feature` |
| `git-` | Version control | `git-commit` |
| `<bare>` | Cross-cutting utility | `verify`, `handoff` |

When adding a new skill: pick the matching prefix. If a clear prefix doesn't exist (you're starting a new group), introduce one and document it here.

### Possible future groups

When the catalog grows past ~10 skills, these prefixes are likely to appear:

- `refactor-*` — `refactor-extract-port`, `refactor-to-decorator`
- `review-*` — `review-dependency-rule`, `review-anemic-model`
- `to-*` — `to-prd`, `to-issues`, `to-changelog`
- `diagnose` — single skill for debug methodology

Add them when there's a real second skill in the group, not pre-emptively (YAGNI).

## How to add a new skill

1. Create a new folder: `.agents/skills/<skill-name>/`
2. Add `SKILL.md` with this frontmatter:

   ```markdown
   ---
   name: <skill-name>
   description: One-line description of what this skill does and when to invoke it.
   ---

   # <Skill Title>

   ...
   ```

3. Add supporting `.md` files in the same folder if the skill needs them; reference them via relative links from `SKILL.md`.
4. Update this README's table.
5. Optional — record version metadata in a `skills-lock.json` if you import skills from external repos (see [dimadev01/club-social](https://github.com/dimadev01/club-social) for an example).

## Why project-local skills (vs. global)

These skills are **tailored to this codebase's conventions** (DDD slices, Repository protocol, `create`/`update` split, Clock port, etc.). They reference real files in this repo. A global skill would have to be generic and lose this specificity.

Anyone cloning this repo gets the skills automatically; no per-developer setup.

## Relationship to AGENTS.md / CLAUDE.md

- **[AGENTS.md](../../AGENTS.md)** — always loaded; describes the project's rules and architecture
- **[CLAUDE.md](../../CLAUDE.md)** — always loaded by Claude Code; delegates to AGENTS.md and adds Claude-specific preferences
- **Skills (here)** — loaded on demand; describe specific workflows

Rule of thumb: if the AI needs to know it for **every** task, it goes in AGENTS.md. If it's a **specific workflow** (add use case, run verify, hand off), it's a skill.
