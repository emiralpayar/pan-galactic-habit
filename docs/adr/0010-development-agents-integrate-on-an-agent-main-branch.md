# 0010. Development agents integrate on an agent-main branch

- **Status:** Accepted
- **Date:** 2026-09-24
- **Deciders:** @emiralpayar, @MGokcay (by approving the PR that adds this ADR)

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

This ADR narrows ADR 0002 for one branch only: ADR 0002 chose short-lived branches off `main` and squash-only merges, and it stands for everything except `agent-main` and the sync merge commits described below.

## Decision

We will:

- Add a long-lived **`agent-main`** branch.
  The maintainers' Claude Code sessions branch from it, open PRs against it, and review, approve, and merge each other's PRs into it, safety-critical ones included.
  The one exception is a PR that declares `Safety-Impact: loosens`: the loop labels it `needs-human`, and a maintainer decides it.
- **Leave `main` unchanged.**
  Its ruleset, code-owner review, human approval, and squash-only history stay as ADR 0002 defines them.
  Nothing deploys from `agent-main`.
- Move work from `agent-main` to `main` only through a **promotion PR** (`agent-main` → `main`) that a human reviews, approves, and squash-merges.
  After a promotion, a sync PR merges `main` back into `agent-main` with a merge commit, so the next promotion diff shows only new work.
  The commit message check skips a promotion's commits and commits already on `main`: their titles were checked when they landed, and GitHub's `(#NN)` suffix can push a squash header past the length limit.
- Protect `agent-main` with its own ruleset (`.github/rulesets/protect-agent-main.json`):
  - a PR is required, with 1 approval, and GitHub forbids approving your own PR, so the approval comes from the other session;
  - the last push must be approved;
  - the same required status checks as `main`, with the branch up to date;
  - no force-push and no deletion;
  - squash for work PRs, and merge commits only for syncs from `main`;
  - review threads need not be resolved, unlike on `main`, because no human is there to resolve a disagreement; the loop's `needs-human` label handles that instead.
- Run each loop session under its **maintainer's own GitHub account**, and mark everything it writes with an **author note**.
  Every PR description, review, comment, and issue the session writes starts with a note saying that a Claude Code loop session wrote it on that maintainer's account, so nobody mistakes it for the maintainer's own words or review.
  Approvals on `agent-main` therefore come from the other maintainer's account, and GitHub still forbids approving your own PR.
- Accept that, for `main`, the hook and the instructions are now the only thing stopping a loop session from approving or merging.
  Both maintainers are code owners, so a session on one maintainer's account *could* give a valid code-owner approval to the other maintainer's PR into `main`; the ruleset cannot tell the session from the person.
  Each maintainer also keeps a user-level copy of the hook's `main` rules in `~/.claude/settings.json`, which a PR to this repository cannot change.
- Let the Claude Code guard hook allow `gh pr merge` and `gh pr review --approve` only for a PR whose base is `agent-main`.
  It keeps blocking both for every other base, refuses any option the loop does not need (`--admin`, `--auto`, `-R`, ...), and blocks retargeting a PR and merging or reviewing through `gh api`.
  The project settings no longer deny `gh pr merge`, so the hook is what gates it.
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
- No new accounts are needed, but GitHub attributes the loop's commits, PRs, and approvals to the maintainers themselves.
  The author note is the only thing that tells them apart from the maintainers' own work, so the sessions must never omit it.
- `main`'s protection against the loop is a guardrail, not a boundary.
  A session that ignores its instructions, or merges a weakened hook into `agent-main` and runs it, could approve and merge into `main` with a maintainer's credentials.
  The user-level hook copy and reviewing every promotion reduce this; separate bot accounts that are not code owners would remove it, and remain the fix if this ever happens.
- The maintainers' tokens can change workflows, and workflow files run with repository secrets from the PR's own branch (see [Claude review](../development/agentic-development.md#claude-review)).
  A loop PR that edits `.github/workflows/` can therefore reach those secrets before a human sees it; promotion reviewers check such PRs on `agent-main` first.
- An agent's approval on `agent-main` is not a human review.
  The humans stay accountable for what they promote.
- There are now two long-lived branches, and `agent-main` can drift from `main`.
  The sync after each promotion keeps the drift to the unpromoted work.
- The repository must allow merge commits so syncs can use them.
  The `protect-main` ruleset still restricts `main` to squash.

## Alternatives considered

- **Separate bot accounts that are not code owners.**
  Would make `main`'s code-owner rule a structural boundary against the loop.
  The maintainers chose their own accounts, marked with an author note, to avoid managing extra accounts and tokens.

- **Let the agents approve and merge into `main`.**
  Removes the human gate for everything that is deployed, including the controls that bound the agents.
  Rejected in favor of an isolated branch.
- **Keep merging human, and let agents only mark a PR `ready-for-human`.**
  Safest, but the humans remain the bottleneck the loop is meant to remove.
- **Let agents merge only non-safety-critical PRs into `agent-main`.**
  Smaller blast radius on `agent-main`, but safety-critical work would stall the loop, and `main` already gets a human review at promotion.
  The maintainers chose full autonomy on `agent-main`.
