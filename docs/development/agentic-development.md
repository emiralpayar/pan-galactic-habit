# Agentic Development

How humans and AI agents build pan-galactic-x together. The rules in [CONTRIBUTING.md](../../CONTRIBUTING.md) apply to everyone; this guide covers what is specific to working with agents.

## Roles

| Role | Identity | Can | Cannot |
|---|---|---|---|
| **Developer** | Their own GitHub account | Author PRs, review and approve *others'* PRs, merge | Approve their own PRs |
| **Claude Code session** (assisted) | The developer's git and GitHub identity | Branch, commit, push branches, open PRs | Commit to or push `main`, approve, merge, bypass hooks |
| **Autonomous agent** (Orchestrator, Improver, lobe) — *future* | A dedicated GitHub bot account | Push `agent/…` branches, open PRs | Approve, merge, write outside its scope |

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
