# 0001. Record architecture decisions

- **Status:** Accepted
- **Date:** 2026-09-15
- **Deciders:** @mgokcay

## Context

pan-galactic-x is built by humans and AI agents together, and later by the system's own agents (Orchestrator, Improver). Agents start every session without memory of past discussions. Without a written record of *why* the architecture is the way it is, agents and new contributors will re-litigate settled decisions or silently contradict them.

ARCHITECTURE.md describes the current architecture but is edited over time, so the reasoning behind past choices gets lost.

## Decision

We will record significant architecture decisions as Architecture Decision Records in `docs/adr/`, using the format in `0000-template.md` and the rules in `docs/adr/README.md`.

ARCHITECTURE.md remains the description of the current architecture and links to ADRs where relevant.

## Consequences

- Decisions and their rationale are reviewable in PRs and discoverable by agents.
- Open questions in ARCHITECTURE.md §11 get resolved through ADRs, which makes the resolution explicit.
- Writing an ADR adds a small cost to significant changes.
- Accepted ADRs are immutable, so the record can accumulate superseded entries.

## Alternatives considered

- **Only ARCHITECTURE.md.** Simpler, but loses the history of why decisions were made and what was rejected.
- **Decisions in PR descriptions or issues.** Hard to discover, and not versioned with the code.
