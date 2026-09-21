# Agentic Development

How humans and AI agents build pan-galactic-habit together. The rules in [CONTRIBUTING.md](../../CONTRIBUTING.md) apply to everyone; this guide covers what is specific to working with agents.

## Roles

| Role | Identity | Can | Cannot |
|---|---|---|---|
| **Developer** | Their own GitHub account | Author PRs, review and approve *others'* PRs, merge | Approve their own PRs |
| **Claude Code session** (assisted) | The developer's git and GitHub identity | Branch, commit, push branches, open PRs | Commit to or push `main`, approve, merge, bypass hooks |
| **Claude GitHub app** (`@claude`) | The Claude app's bot identity | When a collaborator mentions it on an issue, or a PR's author on that PR: comment, push to a `claude/…` branch or that PR's branch | Approve, merge, push `main`, run repository code, run for anyone else |
| **Claude review** (automatic) | The Claude app's bot identity | On a collaborator's non-draft PR: read the checkout, comment | Edit files, run commands, push, approve, request changes, run for forks |
| **Autonomous agent** (Orchestrator, Improver, habit) — *future* | A dedicated GitHub bot account | Push `agent/…` branches, open PRs | Approve, merge, write outside its scope |

**Accountability stays human.** The developer running a session owns every PR it opens; the reviewer who approves an agent-authored PR owns that approval.

## Guardrail layers

| Layer | Applies to | Enforced by |
|---|---|---|
| Instructions | Agents | `AGENTS.md`, `CLAUDE.md`, component READMEs |
| Claude Code permissions and hook | Claude Code sessions | `.claude/settings.json`, `.claude/hooks/guard-git.sh` |
| Local git hooks | Anyone who ran `make setup` | `.githooks/` |
| CI checks | Every PR | `.github/workflows/` |
| Code owners | Every PR | `.github/CODEOWNERS` |
| Repository ruleset | Everyone, no bypass | `.github/rulesets/protect-main.json` |

Each layer catches what the previous one missed. Instructions can be ignored and local hooks skipped; the ruleset cannot. Never weaken a layer on the grounds that another one exists.

## A typical Claude Code session

1. **Start from an issue.** Give the session the issue number.
2. **`/start-work`** — syncs `main` and creates a correctly named branch.
3. **Plan before large changes.** Ask for a plan (or use plan mode) and review it before implementation starts. Correcting a plan is much cheaper than correcting a diff.
4. **Implement in small steps.** Keep the change to one concern.
5. **`make check`** — the session runs it before committing.
6. **Subagent reviews** when relevant:
   - `safety-reviewer` for anything touching safety-critical paths.
   - `architecture-reviewer` for new components or changed interactions.
7. **`/open-pr`** — pushes and opens a draft PR from the template.
8. **You review the PR as if a colleague wrote it**, then request review from someone else.

## Claude on GitHub

Mentioning `@claude` runs `.github/workflows/claude.yml`.

- **Who can trigger it.** The owner or a collaborator, in a new issue or an issue comment. On a pull request, only the PR's author: whoever directs Claude's pushes to a PR must not be the one who approves them.
- **What it produces.** On an issue, commits on a `claude/…` branch and a link to open a PR. On a pull request, commits on that PR's branch. It cannot approve or merge; the usual checks, code owner review, and ruleset apply.
- **Who opens the PR.** The person who mentioned `@claude` opens the PR from its link, so someone else approves it. Don't open a PR from a `claude/…` branch that another person requested.
- **What it reads.** The issue or PR, and comments only from people with write access and from Claude itself. The workflow reads the collaborator list on every run, so adding a collaborator needs no workflow change.
- **What it can write.** Files inside the checkout, and only there: the workflow grants `Edit(/$GITHUB_WORKSPACE/**)`. Anything not granted waits for an approval nobody can give in a headless run, so it is refused.
- **Where its permissions live.** In `claude_args` in the workflow, never in `.claude/settings.json`: Claude Code ignores a project settings file's `permissions.allow` entries until the workspace is trusted through its interactive dialog, and a runner is never trusted. `deny` entries are kept from every source, and so is `--disallowedTools`, so the guardrails hold either way.
- **Why a rule and not a permission mode.** The sandbox `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB` switches on takes the permission modes out of play: with it enabled, `acceptEdits` does not auto-approve writes. Grant file access with an `Edit(<path>)` rule — it covers every file-editing tool, while a `Write(<path>)` rule is ignored by file permission checks.
- **What it cannot run.** Tool rules deny repository code (`make`, `scripts/`), git commands that can run code or print credentials, and access to `.git/`, because on a PR those files come from the PR's branch. Claude therefore never verifies its own work: it pushes a branch and CI runs the same checks. The only build commands it may run are `uv add --no-sync` and `uv lock`, enough to record a dependency without building the checked-out project. The action restores only Claude's own configuration (such as `.claude/`, `CLAUDE.md`, and `.mcp.json`) from the base branch; `AGENTS.md`, which `CLAUDE.md` imports, is read from the checked-out branch. These rules reduce the risk; they are not a sandbox.
- **Untrusted content.** An issue or PR body reaches the model even when someone outside the project wrote it, and its author can edit it until the moment you mention `@claude`. Read it first.
- **Changes to the workflow** are safety-critical, like every file in `.github/workflows/`. Never set `ACTIONS_STEP_DEBUG` on this repository: it makes the action print full tool output to public logs.

## Claude review

`.github/workflows/claude-review.yml` reviews a pull request when it is opened, reopened, or marked ready for review. It does not run on every push; mention `@claude` on your PR to ask for another look.

- **Whose PRs.** Non-draft PRs from a branch in this repository, by the owner or a collaborator. Fork PRs and Dependabot PRs are skipped, so neither gets secrets nor reaches the model.
- **What it does.** Reads the checkout and comments: inline comments on specific lines and a short summary. It checks the change against AGENTS.md, ARCHITECTURE.md, and CONTRIBUTING.md, with extra attention to safety-critical paths and anything that loosens a control.
- **What it cannot do.** Edit files, run commands (there is no Bash tool), push, approve, or request changes. The allow list and deny list are in `claude_args`. Without a command tool, text in a diff cannot make Claude run anything. It can still read files, so deny rules keep it out of `.git/`, `/proc`, and the runner's credential locations, and the checkout keeps no credentials (`persist-credentials: false`). These rules reduce the risk and are not proven to catch every path, such as a symlink committed in a PR. Treat a prompt injection as able to cause a misleading comment and, at worst, an attempt to quote a file.
- **It is advisory.** It is not a required check and does not replace the human review or the `safety-reviewer` agent. A clean review means Claude found nothing, not that the change is safe.
- **The workflow file comes from the PR.** On `pull_request`, a PR can change this workflow and run its own version. That needs write access, as does editing `claude.yml`, and `.github/workflows/` is code-owned, but the review happens at merge: the PR's own version of the workflow runs with the secret before anyone approves it. A collaborator's PR is therefore trusted to that extent.
- **Files come from the PR's branch too.** `AGENTS.md`, `ARCHITECTURE.md`, and the READMEs it reads are the PR's versions. A PR that weakens a rule can weaken what Claude checks it against, so read the diff of those files yourself.

## Parallel sessions

Run each concurrent session in its own git worktree so they never share a working tree or branch:

```bash
git fetch origin
git worktree add ../pan-galactic-12-policy-schema -b feat/12-policy-schema origin/main
cd ../pan-galactic-12-policy-schema && claude
```

Remove it after the PR merges: `git worktree remove ../pan-galactic-12-policy-schema`.

Hooks are shared across worktrees because `core.hooksPath` is stored in the repository config.

## Context files

Agents start every session without memory of previous ones. What they know comes from files, so those files must be accurate.

| File | Audience | Keep in it |
|---|---|---|
| `AGENTS.md` | All agents | Hard rules, workflow, conventions summary, repo map, current phase |
| `CLAUDE.md` | Claude Code | Imports `AGENTS.md`; Claude-specific tooling (skills, subagents, hooks) |
| `<component>/README.md` | Humans and agents | Responsibility, boundaries, change rules for that component |
| `ARCHITECTURE.md` | Humans and agents | The current architecture |
| `docs/adr/` | Humans and agents | Why decisions were made |

Rules:

- **Update context files in the same PR** as the change that makes them stale. A stale `AGENTS.md` misleads every future session.
- **Keep them short and specific.** Every line is loaded into context; prefer pointers to detailed docs over copies.
- **Personal preferences** go in `CLAUDE.local.md` and `.claude/settings.local.json` (gitignored), not in shared files.

## Reviewing AI-authored PRs

AI-written code tends to look plausible, so review with specific attention to:

- **Claims vs. reality.** Does the description say tests were run? Check the CI results. Does it say a case is handled? Find the code.
- **Tests that test something.** A test should fail without the change. Watch for tests that mock the thing under test or assert on nothing meaningful.
- **Scope creep.** Unrelated refactors, renamed variables, reformatted files. Ask for them to be removed.
- **Invented APIs.** Function names, options, or library features that don't exist.
- **Silent decisions.** A new dependency, a chosen library, a storage format — anything that should have been an ADR or at least a sentence in the description.
- **Weakened checks.** Loosened lint rules, skipped tests, broadened regexes, `|| true`, catch-all exception handlers.
- **Secrets and data.** Tokens in examples, real-looking customer data in fixtures.

## Attribution

- Commits from AI-assisted sessions carry a `Co-Authored-By:` trailer for the model.
- The PR template's **AI involvement** field is filled honestly: `none`, `assisted`, or `authored`.
- Squash merges keep commit messages in the body, so attribution survives on `main`.

## When an agent is blocked

If a hook, check, or permission blocks an agent, the correct response is to **stop and report**, not to find another route. If the rule is wrong, change it in a PR — which, for guardrails, is a safety-critical PR reviewed by code owners.
