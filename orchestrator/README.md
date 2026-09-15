# Orchestrator Agent

> **Status:** not started — Phase 3 (ARCHITECTURE.md §12). Do not start until the lobe template has been extracted from the Backlog Refiner.

Talks to the user over chat, designs the lobe a request needs, and opens it as a pull request (ARCHITECTURE.md §2, §4).

## Boundaries

- Produces lobes that follow the extracted template: fresh agent, memory, Safety Policy, and evals; reused chat interface, Safety Layer engine, and adapters.
- Opens PRs from `agent/orchestrator/…` branches under its own bot identity. Never approves or merges.
- Never writes to external systems.
- Session-only (ephemeral) lobes are allowed only if they are read-only (ARCHITECTURE.md §10.2).
