# 0010. Development agents integrate on an agent-main branch

- **Status:** Accepted
- **Date:** 2026-09-24
- **Deciders:** @emiralpayar

## Context

Two maintainers each run a Claude Code session on this repository.
Today every step between the sessions goes through a human: one session opens a PR, a human asks the other session to review it, and a human relays the findings back.
The humans are the bottleneck, and both sessions sit idle for most of their usage window ([#45](https://github.com/emiralpayar/pan-galactic-habit/issues/45)).

The maintainers want the two sessions to run a continuous loop without them:

- one session implements and opens a PR,
- the other reviews it, approves it and merges it,
- both sessions choose their next work and open their own issues.

ARCHITECTURE.md §1 makes human review and merge the single approval gate for every change, and [ADR 0002](0002-trunk-based-development-with-protected-main.md) protects `main` so nothing reaches it without that gate.
Letting agents merge into `main` would remove that gate for everything, including the Safety Layer, the policies, and the guardrails that bound the agents themselves.

## Decision

We will:

- Add a long-lived **`agent-main`** branch.
  The maintainers' Claude Code sessions branch from it, open PRs against it, and review, approve, and merge each other's PRs into it, safety-critical ones included.
- **Leave `main` unchanged.**
  Its ruleset, code-owner review, human approval, and squash-only history stay as ADR 0002 defines them.
  Nothing deploys from `agent-main`.
- Move work from `agent-main` to `main` only through a **promotion PR** (`agent-main` → `main`) that a human reviews, approves, and squash-merges.
  After a promotion, a sync PR merges `main` back into `agent-main` with a merge commit, so the next promotion diff shows only new work.
- Protect `agent-main` with its own ruleset (`.github/rulesets/protect-agent-main.json`):
  - a PR is required, with 1 approval, and GitHub forbids approving your own PR, so the approval comes from the other session;
  - the last push must be approved;
  - the same required status checks as `main`, with the branch up to date;
  - no force-push and no deletion;
  - squash for work PRs, and merge commits only for syncs from `main`.
- Run each loop session under its **own bot GitHub account**.
  The account is a collaborator with write access, is not listed in CODEOWNERS, and holds a token scoped to this repository.
  `main` requires a code-owner approval and CODEOWNERS covers every path, so a bot's approval can never satisfy it: this is what stops an agent from approving into `main`.
  `agent-main` does not require code-owner review, so the bots can approve each other's PRs there.
  Until the bot accounts exist, the loop does not run: a session acting as a maintainer's own account could approve into `main`, and only the hook and instructions would stop it.
- Let the Claude Code guard hook allow `gh pr merge` and `gh pr review --approve` only for a PR whose base is `agent-main`.
  It keeps blocking both for every other base, and blocks `--admin` everywhere.
- Scope this to the maintainers' development sessions.
  The system's own agents (Orchestrator, Improver, running habits) never target `agent-main`, and still may not approve or merge anything (ARCHITECTURE.md §8).

The loop protocol is specified in [agentic development](../development/agentic-development.md#cross-review-loop-on-agent-main) and the `agent-loop` skill.

## Consequences

- The sessions can keep working without a human for a whole usage window.
- `main` keeps every control it has, so ARCHITECTURE.md §1 principle 3 still holds for everything that is deployed.
- Agents can change their own guardrails on `agent-main`: hooks, rulesets, CODEOWNERS, the Safety Layer, and this ADR.
  - A rule changed on `agent-main` takes effect for the sessions working there, and the local hook comes from the checked-out branch.
  - Only a promotion puts such a change in front of a human.
  - A ruleset change still needs an admin to apply it, which the hook keeps blocking.
- The promotion PR can be large.
  Its reviewer must read the safety-critical part of the diff as carefully as a normal PR, and can send work back to `agent-main` instead of promoting it.
  Promote often to keep that review small.
- Two bot accounts must be created and maintained, and their tokens kept out of the repository.
  Commits and PRs from the loop are attributed to the bots, with the maintainer who runs the session named in the PR description.
- An agent's approval on `agent-main` is not a human review.
  The humans stay accountable for what they promote.
- There are now two long-lived branches, and `agent-main` can drift from `main`.
  The sync after each promotion keeps the drift to the unpromoted work.
- The repository must allow merge commits so syncs can use them.
  The `protect-main` ruleset still restricts `main` to squash.

## Alternatives considered

- **Let the agents approve and merge into `main`.**
  Removes the human gate for everything that is deployed, including the controls that bound the agents.
  Rejected in favor of an isolated branch.
- **Keep merging human, and let agents only mark a PR `ready-for-human`.**
  Safest, but the humans remain the bottleneck the loop is meant to remove.
- **Let agents merge only non-safety-critical PRs into `agent-main`.**
  Smaller blast radius on `agent-main`, but safety-critical work would stall the loop, and `main` already gets a human review at promotion.
  The maintainers chose full autonomy on `agent-main`.
