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
- Run each loop session under a **per-maintainer agent account** (for example `emiralpayar-agent`), and mark everything it writes with an **author note**.
  The maintainer creates and controls the account. It is a collaborator with write access, is **not** listed in CODEOWNERS, and holds a token limited to this repository without the `workflow` scope, so it cannot change workflows, repository settings, or rulesets.
  Every PR description, review, comment, and issue the session writes starts with a note naming the agent account and the maintainer it works for.
  GitHub forbids approving your own PR, so every merge into `agent-main` has been approved by the other maintainer's agent account.
  `main` requires a code-owner approval and CODEOWNERS covers every path, so an agent account's approval can never satisfy it: the ruleset, not the hook, stops the loop from approving into `main`.
  A maintainer's own account must never run the loop, because it is a code owner; the hook refuses merges and approvals from a code owner's account.
- Let the Claude Code guard hook allow `gh pr merge` and `gh pr review --approve` only for a PR whose base is `agent-main`.
  It keeps blocking both for every other base, refuses any option the loop does not need (`--admin`, `--auto`, `-R`, ...), and blocks retargeting a PR and merging or reviewing through `gh api`.
  The project settings no longer deny `gh pr merge`; the hook gates it, in front of the rulesets.
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
- Two agent accounts must be created and their tokens kept out of the repository.
  GitHub attributes the loop's commits, PRs, and approvals to the agent accounts, and the author note names the maintainer each one works for.
- An agent account can still merge a PR into `main` that a human has already approved, and could bypass the hook with a script; neither lets anything reach `main` without a code owner's approval.
- A loop PR that edits `.github/workflows/` runs its own workflow version with repository secrets before a human sees it (see [Claude review](../development/agentic-development.md#claude-review)).
  The agent tokens cannot push workflow changes without the `workflow` scope, so such a PR can only come from a maintainer's own account.
- An agent's approval on `agent-main` is not a human review.
  The humans stay accountable for what they promote.
- There are now two long-lived branches, and `agent-main` can drift from `main`.
  The sync after each promotion keeps the drift to the unpromoted work.
- The repository must allow merge commits so syncs can use them.
  The `protect-main` ruleset still restricts `main` to squash.

## Alternatives considered

- **Run the loop on the maintainers' own accounts, with an author note.**
  No extra accounts, but both maintainers are code owners, so a session could give a valid code-owner approval into `main`, and only the hook would stop it.
  A token cannot fix this: GitHub scopes approve and merge permissions to the repository, not to a branch.
- **Let the agents approve and merge into `main`.**
  Removes the human gate for everything that is deployed, including the controls that bound the agents.
  Rejected in favor of an isolated branch.
- **Keep merging human, and let agents only mark a PR `ready-for-human`.**
  Safest, but the humans remain the bottleneck the loop is meant to remove.
- **Let agents merge only non-safety-critical PRs into `agent-main`.**
  Smaller blast radius on `agent-main`, but safety-critical work would stall the loop, and `main` already gets a human review at promotion.
  The maintainers chose full autonomy on `agent-main`.
