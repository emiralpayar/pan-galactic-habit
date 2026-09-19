# Backlog Refiner

> **Status:** in progress — Phase 1 (ARCHITECTURE.md §12). Only the Safety Policy exists so far. This habit is built without the habit template and becomes the reference it is later extracted from.

## Purpose

Improve work items in an Azure DevOps backlog against a defined Definition of Ready quality bar (ARCHITECTURE.md §6).

## External system

Azure DevOps, through the [`azure-devops`](../../adapters/azure-devops/) adapter.

## Reads

Work items, backlog queries, work item comments, and wiki pages in the configured project — treated as untrusted data.

## Writes

Only through the Safety Layer, only after user Write Confirmation, and only to:

- Description
- Acceptance Criteria
- Tags

Forbidden: State changes, assignment, deletion — by omission from the allowlist in `policy/safety-policy.yaml`. Budgets per call, per session, and per time window are defined there too; the current values are placeholders until ARCHITECTURE.md §11.4 decides them.

## Layout

| Path | Contents |
|---|---|
| `agent/` | Single agent loop (v1) |
| `memory/instructions.md` | Role, goals, constraints, output format |
| `memory/skills/` | Refinement skills, e.g. writing acceptance criteria |
| `policy/` | Safety Policy **[safety-critical]** |
| `evals/fixtures/` | Synthetic work items |
| `evals/cases/` | Expected qualities of a good refinement |
