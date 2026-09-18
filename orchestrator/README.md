# Orchestrator Agent

> **Status:** not started — Phase 3 (ARCHITECTURE.md §12). Sequenced after the habit template is extracted, to dogfood it against a real habit-request issue first, though the Orchestrator itself has no direct dependency on the template — see ARCHITECTURE.md §12.

Talks to the user over chat, clarifies what a new habit needs to do, and opens a habit-request issue capturing it (ARCHITECTURE.md §2, §4; [ADR 0007](../docs/adr/0007-orchestrator-opens-habit-request-issues-not-prs.md)). It does not design or implement the habit itself — implementation happens separately, through the normal issue → branch → PR workflow, picked up by a human or an AI agent (e.g. via `@claude` assignment), which generates the habit against the extracted template.

## Boundaries

- Habit-request issues follow `.github/ISSUE_TEMPLATE/habit_request.yml` and must be specific enough for the template to be applied: fresh agent, memory, Safety Policy, and evals; reused chat interface, Safety Layer engine, and adapters.
- Opens GitHub issues under its own bot identity. Never opens PRs, pushes branches, approves, or merges.
- Never writes to external systems.
- Never assembles or runs a habit itself, not even ephemerally — every habit, without exception, is generated and reviewed through the normal issue → branch → PR workflow ([ADR 0007](../docs/adr/0007-orchestrator-opens-habit-request-issues-not-prs.md); ARCHITECTURE.md §10.2).
