# Orchestrator Agent

> **Status:** not started — Phase 3 (ARCHITECTURE.md §12). Do not start until the habit template has been extracted from the Backlog Refiner.

Talks to the user over chat, clarifies what a new habit needs to do, and opens a habit-request issue capturing it (ARCHITECTURE.md §2, §4; [ADR 0007](../docs/adr/0007-orchestrator-opens-habit-request-issues-not-prs.md)). It does not design or implement the habit itself — implementation happens separately, through the normal issue → branch → PR workflow, picked up by a human or an AI agent (e.g. via `@claude` assignment).

## Boundaries

- Habit-request issues follow `.github/ISSUE_TEMPLATE/habit_request.yml` and must be specific enough to drive the extracted template: fresh agent, memory, Safety Policy, and evals; reused chat interface, Safety Layer engine, and adapters.
- Opens GitHub issues under its own bot identity. Never opens PRs, pushes branches, approves, or merges.
- Never writes to external systems.
- Session-only (ephemeral) habits are allowed only if they are read-only (ARCHITECTURE.md §10.2).
