# Contributing

This document defines how every change reaches `main` — whether it is written by a human, a Claude Code session, or one of the system's own agents. The rules are the same for everyone.

**Contents**

1. [Ground rules](#ground-rules)
2. [Development setup](#development-setup)
3. [Workflow](#workflow)
4. [Issues](#issues)
5. [Branch naming](#branch-naming)
6. [Commit messages](#commit-messages)
7. [Pull requests](#pull-requests)
8. [Code review](#code-review)
9. [Safety-critical changes](#safety-critical-changes)
10. [Architecture changes and ADRs](#architecture-changes-and-adrs)
11. [Habits: memory, policy, and evals](#habits-memory-policy-and-evals)
12. [AI-assisted and agent-authored contributions](#ai-assisted-and-agent-authored-contributions)
13. [Coding standards](#coding-standards)
14. [Secrets and data](#secrets-and-data)
15. [Dependencies](#dependencies)
16. [Versioning and releases](#versioning-and-releases)
17. [Labels](#labels)
18. [How the rules are enforced](#how-the-rules-are-enforced)

---

## Ground rules

- **`main` is protected.** No direct commits, no direct pushes, no force-pushes, no exceptions — administrators included.
- **Every change is a pull request** that passes CI. A pull request into `main` is approved by at least one human who did not author it.
- **Squash merge only** into `main`. One PR becomes one commit on `main`, and the PR title becomes its message. (A sync from `main` into `agent-main` uses a merge commit.)
- **Bots and agents may open PRs; they may never approve or merge them into `main`.** Development loop sessions cross-review and merge each other's PRs only on the `agent-main` integration branch; a human promotes that work to `main` ([ADR 0010](docs/adr/0010-development-agents-integrate-on-an-agent-main-branch.md)).
- **Small, focused PRs.** One concern per PR.
- **Docs change with the code.** A PR that changes architecture updates ARCHITECTURE.md in the same PR.

---

## Development setup

Prerequisites: `git`, `bash`, `make`, and the [GitHub CLI](https://cli.github.com/) (`gh`). Recommended: `shellcheck` and Node.js (for `npx markdownlint-cli2`). For Python work, also install [uv](https://docs.astral.sh/uv/), which provides the pinned Python version ([ADR 0003](docs/adr/0003-use-python-as-the-implementation-language.md)).

```bash
make setup   # points git at .githooks/, sets the commit template, enables fetch pruning
make sync    # installs the pinned Python and every workspace package from uv.lock
make check   # runs the convention checks, linters, type checks, tests, and import contracts CI runs
make help    # lists all targets
```

`make setup` is required once per clone. It installs hooks that stop you from committing to `main` and that validate branch names and commit messages before CI does.

---

## Workflow

We use **trunk-based development**: `main` is always releasable, and all work happens on short-lived branches that are merged back through PRs within days, not weeks.

```text
issue ──► branch from main ──► commits ──► push ──► draft PR ──► checks green
      ──► ready for review ──► approval ──► squash merge ──► branch deleted ──► deploy (commit SHA)
```

1. **Pick or open an issue.** Assign it to yourself.
2. **Branch from an up-to-date `main`:**

   ```bash
   git switch main && git pull --ff-only
   git switch -c feat/12-safety-policy-schema
   ```

3. **Commit early and often** using [Conventional Commits](#commit-messages).
4. **Keep your branch current** by rebasing on `main`: `git fetch && git rebase origin/main`, then `git push --force-with-lease`. Rebasing your own branch is fine; plain `--force` is not.
5. **Open a draft PR early** to get CI feedback and signal work in progress.
6. **Mark it ready for review** when checks are green and the author checklist is complete.
7. **Address review feedback** with new commits (they are squashed on merge, so no need to rewrite history during review).
8. **A reviewer approves; the author (or a reviewer) squash-merges.** The branch is deleted automatically.

Branches should live **less than a week**. If work is bigger, split it — use feature flags or incomplete-but-inert code rather than long-lived branches. The one long-lived branch is `agent-main`, the development loop's integration branch ([ADR 0010](docs/adr/0010-development-agents-integrate-on-an-agent-main-branch.md)); loop work follows the same flow with `agent-main` in place of `main`.

---

## Issues

- Every non-trivial change starts with an issue. Typos and one-line doc fixes may skip this.
- Use the issue templates: **Bug report**, **Feature request**, or **Habit request**.
- An issue should state the problem and the acceptance criteria, not just a solution.
- Reference issues from branches (`feat/12-…`) and PRs (`Closes #12`).

---

## Branch naming

```text
<type>/<issue>-<short-description>
<type>/<short-description>                        # when there is no issue
agent/<agent>/<type>/<issue>-<short-description>  # autonomous system agents only
```

| Part | Rule |
|---|---|
| `<type>` | One of the [commit types](#types) |
| `<issue>` | The GitHub issue number, when there is one |
| `<short-description>` | Lowercase kebab-case, `a-z`, `0-9`, and `-` only; a few words |
| `<agent>` | `orchestrator`, `improver`, or `habit-<habit-name>` |
| Length | 80 characters maximum |

**Examples**

```text
feat/12-safety-policy-schema
fix/31-ado-adapter-pagination
docs/add-memory-style-guide
chore/bump-node-version
agent/orchestrator/feat/55-release-notes-habit
agent/habit-backlog-refiner/fix/60-clarify-dor-skill
```

**Allowed exceptions** (generated by tools): `dependabot/…`, GitHub's `revert-…`, and the Claude GitHub app's `claude/…` branches. `agent-main` is also accepted, as the head of a promotion PR into `main` ([ADR 0010](docs/adr/0010-development-agents-integrate-on-an-agent-main-branch.md)); nobody commits or pushes to it directly.

Validate locally: `scripts/checks/branch-name.sh`.

---

## Commit messages

We follow [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/).

```text
<type>(<scope>)!: <subject>
<blank line>
<body>
<blank line>
<footer(s)>
```

### Types

| Type | Use for |
|---|---|
| `feat` | A new capability for users or habits |
| `fix` | A bug fix |
| `docs` | Documentation only (including ARCHITECTURE.md and ADRs) |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `perf` | Performance improvement |
| `test` | Adding or fixing tests or evals |
| `build` | Build system, container image, packaging |
| `ci` | CI workflows and repository automation |
| `chore` | Maintenance that fits nothing above |
| `revert` | Reverting a previous commit |

> **Memory changes** to a habit are `feat` (new behavior) or `fix` (corrected behavior), scoped to the habit — because memory *is* behavior.

### Scopes

The scope is optional but strongly encouraged. It must be one of:

| Scope | Area |
|---|---|
| `<habit-name>` | Any directory under `habits/`, e.g. `backlog-refiner` |
| `<adapter-name>` | Any directory under `adapters/`, e.g. `azure-devops` |
| `safety-layer` | Safety Layer engine |
| `adapters` | Cross-adapter contracts and shared adapter code |
| `orchestrator` | Orchestrator Agent |
| `improver` | Improver Agent |
| `chat` | Chat interface |
| `evals` | Shared eval harness |
| `deploy` | Container and deployment |
| `ci` | GitHub workflows |
| `dev` | Developer and agent tooling: `.claude/`, `.githooks/`, `scripts/`, `Makefile` |
| `deps` | Dependency updates |
| `docs` | Documentation spanning several areas |
| `repo` | Repository-wide configuration |

Scopes for habits and adapters are discovered automatically from the directory names, so adding a habit adds its scope.

### Subject

- Imperative mood: "add", not "added" or "adds".
- Lowercase first letter; no trailing period.
- The whole header is **72 characters or fewer**.
- Say *what* changes, specifically: `fix(azure-devops): retry on 429 responses`, not `fix: bug`.

### Body

- Separated from the header by a blank line.
- Explains **why** the change was made and any context a future reader needs. The diff already shows *what*.
- Wrap at 72 characters.

### Footers

| Footer | Meaning |
|---|---|
| `BREAKING CHANGE: <description>` | Incompatible change (also mark the header with `!`) |
| `Refs: #123` | Related issue |
| `Co-Authored-By: Name <email>` | Co-author, including AI models (see [attribution](#attribution)) |

### Examples

```text
feat(safety-layer): enforce per-session write budgets

Budgets were only enforced per call, so an agent could exceed the
intended limit by splitting a batch across many calls.

Refs: #18
```

```text
fix(backlog-refiner)!: stop writing to the Tags field

Tags are used by the triage team for routing; the refiner overwrote them.

BREAKING CHANGE: the refiner's safety policy no longer allows Tags writes.
Refs: #42
```

Accepted without validation: `fixup!` / `squash!` / `amend!` commits (for your branch only — they are squashed away), merge commits, and `Revert "…"` messages generated by git or GitHub.

Validate locally: `scripts/checks/commit-message.sh --message "feat(chat): add history"`. The `commit-msg` hook does this automatically after `make setup`.

---

## Pull requests

### Title

The PR title **must** be a valid Conventional Commit header. On squash merge it becomes the commit message on `main`, so it is checked by CI with the same rules as commits (without the `fixup!` exception).

### Description

Use the PR template. Every PR must include:

- **Summary** — what changes and why.
- **Linked issue** — `Closes #123` (or why there isn't one).
- **`Safety-Impact:`** — `none`, `neutral`, `tightens`, or `loosens`. See [Safety-critical changes](#safety-critical-changes).
- **Verification** — how you know it works.
- **AI involvement** — `none`, `assisted`, or `authored`.

### Size and scope

- **One concern per PR.** A refactor and a feature are two PRs.
- **Aim for under ~400 changed lines** (excluding generated files and fixtures). Larger PRs get worse reviews.
- Don't mix formatting-only changes with logic changes.

### Lifecycle

- Open as **draft** while work is in progress.
- **Ready for review** means: CI green, template complete, self-reviewed.
- Keep the branch up to date with `main` (required before merging).
- All review conversations must be resolved before merging.
- **Squash merge** is the only merge method. Branches are deleted after merge.
- Stale PRs (no activity for 14 days) should be closed or revived by their author.

---

## Code review

### Who reviews

- At least **one approval** from someone other than the author is required.
- **Code owners** (`.github/CODEOWNERS`) must approve changes to paths they own.
- Approvals are dismissed when new commits are pushed, and the most recent push must be approved by someone other than its pusher.
- **Bots and agents cannot approve a PR into `main`.** (On `agent-main`, loop sessions approve each other's PRs; see [agentic development](docs/development/agentic-development.md#cross-review-loop-on-agent-main).) A PR into `main` authored by an agent needs a human approval; a PR authored by a human in a Claude Code session is still that human's PR and needs a *different* human to approve.

### Expectations

- **First response within one business day.** A response can be "I'll get to this tomorrow."
- Review the **diff**, not the description. Verify claims — especially in AI-authored PRs.
- For habit changes, look at the **eval before/after**, not only the text.
- Approve when the change is good enough and moves things forward; perfection is not the bar.

### Comment prefixes

Use [Conventional Comments](https://conventionalcomments.org/) so authors know what is blocking:

| Prefix | Meaning |
|---|---|
| `issue (blocking):` | Must be addressed before merge |
| `suggestion:` | Recommended change, author decides |
| `question:` | Need clarification |
| `nit:` | Minor, non-blocking |
| `praise:` | Something done well |
| `thought:` | Idea for later, non-blocking |

---

## Safety-critical changes

These paths control what the system can do to external systems, or control the guardrails themselves:

| Path | Why |
|---|---|
| `safety-layer/` | The write-gating engine |
| `adapters/` | Request allowlists and pinned API and MCP server versions |
| `habits/*/policy/` | What each habit may write |
| `.github/workflows/`, `.github/rulesets/`, `.github/CODEOWNERS` | CI checks and repository protection |
| `.githooks/`, `.claude/settings.json`, `.claude/hooks/`, `.claude/skills/agent-loop/` | Local guardrails for humans and agents, and the agent loop's review protocol |
| `scripts/checks/`, `scripts/lib/` | The convention and safety checks themselves |
| `pyproject.toml`, `uv.lock`, `.python-version` (repository root) | Dependency sources and pins for every workspace member, and the import contracts |

The authoritative list is `scripts/checks/safety-critical-paths.txt`; keep it in sync with `.github/CODEOWNERS`.

When a PR touches any of them:

1. The **Safety guard** check labels the PR `safety-critical`.
2. The PR description must set `Safety-Impact:` to something other than `none`:
   - `neutral` — touches safety-critical files without changing what is allowed (e.g. a refactor, a test).
   - `tightens` — something that was allowed no longer is.
   - `loosens` — something that was not allowed now is. **Explain exactly what, and why**, in the description.
3. **Code owner approval** is required.
4. Claude Code sessions should run the `safety-reviewer` subagent before opening the PR.

A PR that loosens a control and a PR that does anything else are **separate PRs**.

---

## Architecture changes and ADRs

- **ARCHITECTURE.md describes the current architecture.** If your PR changes it, update the document in the same PR.
- **ADRs record why.** Write an ADR in [`docs/adr/`](docs/adr/) when you make a decision that is hard to reverse, affects multiple components, resolves an open question in ARCHITECTURE.md §11, or chooses between reasonable alternatives.
- ADRs are immutable once accepted. To change a decision, write a new ADR that supersedes the old one.
- Use `make adr title="short title"` or the `new-adr` skill to create one.

---

## Habits: memory, policy, and evals

- Follow the habit template in ARCHITECTURE.md §5 and the structure in [`habits/README.md`](habits/README.md).
- Memory files follow the [memory style guide](docs/development/memory-style-guide.md) — notably **one sentence per line** so diffs are reviewable.
- A change to a habit's behavior or memory must add or update eval cases that demonstrate it (enforced once the eval harness exists).
- A change to a habit's policy is safety-critical.
- Eval fixtures must be synthetic or fully anonymized.

---

## AI-assisted and agent-authored contributions

AI-generated code is welcome and held to exactly the same standard as human code. **The human who opens or approves a PR is accountable for it.**

### Attribution

- Commits written with AI assistance include a `Co-Authored-By:` trailer naming the model, e.g. `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.
- Do not strip attribution trailers. The squash merge preserves them (the squash message is built from commit messages).
- Set **AI involvement** in the PR template honestly.

### Identities

- **Claude Code sessions** run under the developer's own git and GitHub identity. The developer owns the PR and cannot approve it.
- **Development loop sessions** ([ADR 0010](docs/adr/0010-development-agents-integrate-on-an-agent-main-branch.md)) run under a per-maintainer agent account (a collaborator with write access, not a code owner) and start everything they write on GitHub with an author note. They work only on `agent-main`, where they approve and merge the other agent account's PRs; they can never satisfy `main`'s code owner review.
- **Autonomous agents** (Orchestrator, Improver, habits) use their **own** GitHub bot identities and branch names under `agent/…`. They can open PRs, never approve or merge.
- **The Claude GitHub app** (`@claude`) runs under its own bot identity when a collaborator mentions it on an issue, or a PR's author mentions it on that PR. It pushes to a `claude/…` branch or to that PR's branch; it never approves or merges. See [agentic development](docs/development/agentic-development.md#claude-on-github).

### Expectations for AI agents

See [AGENTS.md](AGENTS.md) and [docs/development/agentic-development.md](docs/development/agentic-development.md).

---

## Coding standards

- **EditorConfig** (`.editorconfig`) defines whitespace, line endings (LF), and indentation. Configure your editor to honor it.
- **File and directory names:** lowercase kebab-case (`safety-policy.yaml`, `backlog-refiner/`), unless a language convention requires otherwise.
- **Markdown** is linted with markdownlint (`.markdownlint-cli2.jsonc`).
- **Shell scripts** must pass `shellcheck`, start with `set -euo pipefail`, and remain compatible with bash 3.2 (macOS default).
- **Python** ([ADR 0003](docs/adr/0003-use-python-as-the-implementation-language.md)):
  - Python 3, with the exact version pinned in `.python-version` (3.13 at adoption), managed with uv and a committed `uv.lock`.
  - One uv workspace; each component is a member with its own `pyproject.toml` and a `src/` layout.
  - `ruff format` and `ruff check` for formatting and linting, `mypy --strict` for types, `pytest` for tests.
  - Pydantic models at trust boundaries: policy files, tool inputs, and data read from external systems.
  - import-linter contracts enforce the boundary check (ARCHITECTURE.md §4.2).
  - CI enforces these in `.github/workflows/python.yml`; `make check` runs the same checks locally.
  - Add or remove dependencies with `uv add` / `uv remove` in the member's directory and commit the updated `uv.lock`.
- **Tests:** new behavior comes with tests. Bug fixes come with a test that fails without the fix.
- **Comments** explain *why*, not *what*.

---

## Secrets and data

- **Never commit secrets.** Use `.env` locally (gitignored) and a secret manager in deployed environments. `.env.example` documents the variables with placeholder values.
- If you commit a secret by accident, **treat it as compromised**: rotate it immediately, then remove it from history. Tell the maintainers.
- **No real customer or production data** in the repository — not in fixtures, examples, screenshots, or issues.
- See [SECURITY.md](SECURITY.md) for reporting vulnerabilities.

---

## Dependencies

- Pin versions exactly (lock files, pinned API and MCP server versions, pinned GitHub Actions major versions).
- A new dependency needs a one-line justification in the PR description: what it does and why we can't reasonably do without it.
- Dependabot opens update PRs weekly; they go through the same review.
- **Dependabot PR titles are checked like any other PR title**, except for the length limit. Dependabot sometimes capitalizes the subject (`ci(deps): Bump …`); when the PR title check fails, edit the title to lowercase (`ci(deps): bump …`) before merging, and re-check it right before merging because Dependabot may rewrite it when it updates the PR. Its individual commit messages are not checked, since they are squashed away.

---

## Versioning and releases

- **Deploys are commits.** Every merge to `main` produces an image tagged with the commit SHA (ARCHITECTURE.md §4.4).
- **Releases** are tagged on `main` with [Semantic Versioning](https://semver.org/) (`v0.1.0`). While we are below `1.0.0`, minor versions may contain breaking changes.
- **Release notes** are generated by GitHub from merged PR titles and labels (`.github/release.yml`) — another reason PR titles matter.
- The version bump follows the commits since the last tag: `feat` → minor, `fix`/`perf` → patch, `!`/`BREAKING CHANGE` → major (minor while below 1.0.0).

---

## Labels

| Label | Applied | Meaning |
|---|---|---|
| `safety-critical` | Automatically (Safety guard) | Touches a safety-critical path |
| `memory` | Automatically (labeler) | Changes habit memory |
| `behavior` | Automatically (labeler) | Changes agent, orchestrator, improver, or interface code |
| `docs` | Automatically (labeler) | Documentation changes |
| `dev-tooling` | Automatically (labeler) | Developer and agent tooling |
| `ci` | Automatically (labeler) | CI workflows |
| `dependencies` | Automatically (Dependabot) | Dependency updates |
| `bug`, `enhancement`, `habit-request` | Issue templates | Issue type |
| `needs-adr` | Manually | A decision must be recorded before merging |
| `agent:orchestrator`, `agent:improver`, `agent:habit` | By the agent | Authored by an autonomous agent |

Labels are created by `scripts/bootstrap-github.sh`.

---

## How the rules are enforced

Rules are enforced in layers, so one missing layer does not open a gap.

| Layer | Where | What it enforces |
|---|---|---|
| Local git hooks | `.githooks/` (after `make setup`) | No commits on or pushes to `main` and `agent-main`, branch names, commit messages |
| Claude Code hook | `.claude/hooks/guard-git.sh` | Same, plus no `--no-verify`, force-push, or protection changes by the agent, and PR merge/approval only for PRs into `agent-main` |
| CI checks | `.github/workflows/` | Branch name, PR title, commit messages, safety guard, lints |
| CODEOWNERS | `.github/CODEOWNERS` | Mandatory owners for safety-critical paths |
| GitHub rulesets | `.github/rulesets/protect-main.json` | PR-only `main`, code owner approval, required checks, squash only, linear history, no force-push or deletion — with **no bypass actors** |
| | `.github/rulesets/protect-agent-main.json` | PR-only `agent-main`, one approval by someone other than the last pusher, required checks, no force-push or deletion ([ADR 0010](docs/adr/0010-development-agents-integrate-on-an-agent-main-branch.md)) |

Local hooks are a convenience and can be skipped; the GitHub ruleset cannot.
