# Backlog Refiner

> **Status:** not started — Phase 1 (ARCHITECTURE.md §12). This lobe is built by hand and becomes the reference for the lobe template.

## Purpose

Improve work items in an Azure DevOps backlog against a defined Definition of Ready quality bar (ARCHITECTURE.md §6).

## External system

Azure DevOps, through the [`azure-devops`](../../adapters/azure-devops/) adapter.

## Reads

Work items, backlogs, and wiki pages — treated as untrusted data.

## Writes

Only through the Safety Layer, only after user Write Confirmation, and only to:

- Description
- Acceptance Criteria
- Tags

Forbidden: State changes, assignment, deletion. Budgets per call, per session, and per time window are defined in `policy/safety-policy.yaml` (values to be decided — ARCHITECTURE.md §11).

## Layout

| Path | Contents |
|---|---|
| `agent/` | Single agent loop (v1) |
| `memory/instructions.md` | Role, goals, constraints, output format |
| `memory/skills/` | Refinement skills, e.g. writing acceptance criteria |
| `policy/` | Safety Policy **[safety-critical]** |
| `evals/fixtures/` | Synthetic work items |
| `evals/cases/` | Expected qualities of a good refinement |
