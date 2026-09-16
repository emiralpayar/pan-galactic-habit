# Improver Agent

> **Status:** not started — Phase 4 (ARCHITECTURE.md §12). Built last, once real operational data exists.

Analyzes signals from the Operational Store and eval results, and opens improvement PRs for existing habits (ARCHITECTURE.md §2, §10.4).

## Boundaries

- Reads the Operational Store and eval results; never changes behavior except through a PR.
- Opens PRs from `agent/improver/…` branches under its own bot identity. Never approves or merges.
- Never writes to external systems.
- A proposal that loosens a Safety Policy is a separate PR with `Safety-Impact: loosens`.
