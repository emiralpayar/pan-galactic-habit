# 0002. Trunk-based development with a protected main

- **Status:** Accepted
- **Date:** 2026-09-15
- **Deciders:** @mgokcay

## Context

ARCHITECTURE.md makes the pull request the single approval gate for every change, whether authored by a human, a Claude Code session, or an autonomous agent. That gate is only meaningful if nothing can reach `main` without it — including administrators and agents with push access.

The deploy model maps every running deployment to one commit on `main`, so `main` must always be releasable and its history must be easy to read and revert.

Several of the authors will be AI agents, so conventions must be machine-checkable rather than relying on judgment.

## Decision

We will:

- Use **trunk-based development**: short-lived branches off `main`, merged back through PRs.
- **Protect `main` with a GitHub ruleset** (`.github/rulesets/protect-main.json`) with no bypass actors: PR required, at least one approval from a non-author, code owner review, approval of the last push, resolved conversations, required status checks, up-to-date branches, linear history, no force-push, no deletion.
- Allow **squash merge only**, using the PR title as the commit header.
- Enforce **Conventional Commits** for commit messages and PR titles, and a **branch naming convention**, with checks shared between local git hooks and CI (`scripts/checks/`).
- Mark **safety-critical paths** that require a `Safety-Impact` declaration and code owner review.
- Add **layered guardrails**: local git hooks, a Claude Code hook, CI checks, CODEOWNERS, and the ruleset.

The conventions are specified in CONTRIBUTING.md.

## Consequences

- No one, including admins and agents, can change `main` without review.
- `main` history is one commit per PR with a meaningful, parseable message, which enables generated release notes and simple reverts.
- A solo contributor cannot merge their own PR; at least two people with write access are required.
- Required check names are referenced by the ruleset, so renaming a CI job requires updating the ruleset in the same PR.
- Rulesets on private repositories require a paid GitHub plan for the owning account.
- Some friction for small changes, accepted in exchange for a consistent gate.

## Alternatives considered

- **GitFlow (develop/release branches).** Adds long-lived branches and merge overhead without benefit for a continuously deployed system.
- **Classic branch protection instead of rulesets.** Works, but rulesets can be versioned as JSON in the repository, support merge method restrictions, and apply to admins by default.
- **Merge commits or rebase merges.** Preserve individual commits, but make `main` history noisy and harder to revert per PR.
- **Conventions by documentation only.** Not reliable with AI agents as frequent authors.
