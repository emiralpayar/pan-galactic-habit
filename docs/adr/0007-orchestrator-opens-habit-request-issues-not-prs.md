# 0007. Orchestrator opens habit-request issues, not PRs

- **Status:** Proposed
- **Date:** 2026-09-16
- **Deciders:** MGokcay

## Context

ARCHITECTURE.md §2 defines the Orchestrator Agent as the agent that talks to the user over chat, designs the habit the request needs, and opens it as a PR. §4's Change Flow diagram reflects this as a single step: `ORC -- "new habit draft" --> PR`. §8's Trust Boundaries table gives the Orchestrator the ability to "push to non-main branches, open PRs."

This conflates two different activities in one agent session:

- **Requirements-gathering**: a conversational, back-and-forth activity with the user to work out what a new habit should do, read, write, and never do — exactly what `.github/ISSUE_TEMPLATE/habit_request.yml` already asks for.
- **Implementation**: writing the agent definition, memory, Safety Policy, and Eval Suite so they actually satisfy ARCHITECTURE.md §5 (the Habit Runtime Template), and getting them right against the Safety Layer's structural guarantees.

Requiring the same Orchestrator session to do both means it must be capable of full habit implementation to handle even a simple request. Meanwhile, the repository already has the pieces to run implementation as its own step: a habit-request issue template capturing exactly the fields a habit needs, the standard issue → branch → PR workflow in AGENTS.md, and a connected `@claude` GitHub App (issue #6) that can implement from an assigned issue and open the PR itself.

Full problem statement and rationale: [issue #9](https://github.com/emiralpayar/pan-galactic-refiner/issues/9).

## Decision

We will split the Orchestrator's role for **new habit creation only** into two phases, connected by a GitHub issue instead of an inline handoff:

1. The Orchestrator chats with the user, asking clarifying questions until it has everything `.github/ISSUE_TEMPLATE/habit_request.yml` requires (purpose, external system, reads, writes, forbidden operations, budgets, examples).
2. The Orchestrator opens a habit-request issue with those answers filled in. It no longer designs the habit's agent, memory, Safety Policy, or evals, and it no longer opens a PR.
3. Implementation happens entirely through the workflow AGENTS.md already documents for any change (branch, implement, `make check`, PR): a human picks up the issue, or it is assigned or `@claude`-mentioned so a cloud Claude Code session implements the habit and opens the PR.

This does not change the Improver Agent or habit self-proposal flows in §4.1 — both continue to open PRs directly, as documented today.

## Consequences

**Easier:**

- The Orchestrator's job shrinks to something a chat-only agent can do well: eliciting a complete, well-formed spec. It no longer needs the full capability set (repo conventions, ARCHITECTURE.md §5 template, Safety Policy authoring) required to implement a habit correctly.
- Habit creation reuses the exact same reviewed path as every other change in the repository (issue → branch → PR), instead of a separate Orchestrator-specific PR-opening mechanism.
- Implementation can be picked up by a human or an AI agent interchangeably, since both start from the same issue.

**Harder:**

- Habit creation now has an extra handoff: a user asking the Orchestrator for a habit does not get a PR directly from that conversation — someone (human or `@claude`) still has to pick up the issue.
- The Orchestrator's own trust boundary (§8) needs to be narrowed from "push to non-main branches, open PRs" to "open issues," which is a behavior change for any code already assuming the old boundary.
- Two authoring paths now exist for repository changes stemming from the Orchestrator: an issue-first path for new habits, versus the direct-PR path still used by the Improver and by habit self-proposals. Contributors and future ADRs need to keep this asymmetry straight.

## Alternatives considered

- **Keep the Orchestrator opening PRs directly (status quo).** Rejected: forces one agent session to both gather requirements conversationally and implement a full habit correctly against ARCHITECTURE.md §5, which is a wider capability requirement than a chat-focused agent needs, and duplicates the issue-driven workflow the rest of the repository already uses.
- **Use GitHub's native Copilot coding agent instead of `@claude` for the implementation step.** Rejected for now: the `@claude` GitHub App is already connected (issue #6) and requires no new setup; Copilot's coding agent would need to be configured separately with no clear benefit for this decision. Nothing here precludes adding it later.
- **Apply the issue-first split to the Improver and habit self-proposal flows too.** Rejected: those flows are already narrower and autonomous (reacting to Operational Store signals or a habit's own detected gaps) rather than open-ended conversational requests, so the conflation this ADR addresses does not apply to them. Revisit only if a similar problem shows up there.
