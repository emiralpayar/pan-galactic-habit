# Azure DevOps Adapter

> **Status:** not started — Phase 1. **Safety-critical.**

Integrates Azure DevOps through its REST API ([ADR 0005](../../docs/adr/0005-azure-devops-adapter-calls-the-rest-api-directly.md), ARCHITECTURE.md §6).
The adapter calls the API directly at pinned `api-version`s; it does not use the Azure DevOps MCP server.

## Operations

The adapter can send only these requests; anything else is rejected before it is sent.
The identifier is the operation name Safety Policies use (`safety-layer/README.md`).

| Operation | Identifier | Kind | Request (api-version at adoption) | Limits |
|---|---|---|---|---|
| Get work items | `get-work-items` | read | `GET _apis/wit/workitems` (7.1) | Items from other projects are dropped |
| Find work items | `find-work-items` | read | `POST _apis/wit/wiql` (7.1) | Built from structured filters; the agent never supplies WIQL; `[System.TeamProject] = @project` is always added; results are capped |
| Get work item comments | `get-work-item-comments` | read | `GET _apis/wit/workItems/{id}/comments` (7.1-preview.4) | Configured project only |
| Get wiki page | `get-wiki-page` | read | `GET _apis/wiki/wikis/{wikiIdentifier}/pages` (7.1) | Configured wikis only |
| Update work item | `update-work-item` | write, Safety Layer only | `PATCH _apis/wit/workitems/{id}` (7.1) | Integer id in the configured project; query string is `api-version` only; JSON Patch starts with a `test` on `/rev` from the preview read |

Read volume is also capped per session.
A write rejected because the revision changed fails closed and is shown to the user; it is never retried automatically.

## Credentials

- Token scopes: Work Items (Read & write) and Wiki (Read).
- Those scopes still allow changing state, assigning, and deleting work items, so the identity's project permissions must deny them (ARCHITECTURE.md §6); the Safety Layer is the inner boundary, not the only one.

## To be defined in Phase 1

- The identity writes run under (see ARCHITECTURE.md §11, write identity).
- Pagination, retry, and rate-limit handling.
- The caps for query results and per-session reads.
