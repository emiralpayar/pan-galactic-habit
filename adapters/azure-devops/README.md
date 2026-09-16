# Azure DevOps Adapter

> **Status:** not started — Phase 1. **Safety-critical.**

Integrates Azure DevOps through its REST API ([ADR 0005](../../docs/adr/0005-azure-devops-adapter-calls-the-rest-api-directly.md), ARCHITECTURE.md §6).
The adapter calls the API directly at pinned `api-version`s; it does not use the Azure DevOps MCP server.

## Operations

Nothing outside this allowlist is reachable.

| Operation | Kind | Endpoint (api-version) |
|---|---|---|
| Get work items | read | `GET _apis/wit/workitems` (7.1) |
| Query work items | read | `POST _apis/wit/wiql` (7.1) |
| Get work item comments | read | `GET _apis/wit/workItems/{id}/comments` (7.1-preview.4) |
| Get wiki page | read | `GET _apis/wiki/wikis/{wikiIdentifier}/pages` (7.1) |
| Update work item | write, Safety Layer only | `PATCH _apis/wit/workitems/{id}` (7.1), a JSON Patch that starts with a `test` on `/rev` |

## To be defined in Phase 1

- The credential model and minimum permission scopes (see ARCHITECTURE.md §11, write identity).
- Pagination, retry, and rate-limit handling.
