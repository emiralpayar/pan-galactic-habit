# Azure DevOps Adapter

> **Status:** in progress — Phase 1. **Safety-critical.** Reads of work items are implemented; backlog queries, comments, wiki pages, and the write request builder are not.

Integrates Azure DevOps through its REST API ([ADR 0005](../../docs/adr/0005-azure-devops-adapter-calls-the-rest-api-directly.md), ARCHITECTURE.md §6).
The adapter calls the API directly at pinned `api-version`s; it does not use the Azure DevOps MCP server.

## Operations

The adapter can send only these requests; anything else is rejected before it is sent.
The identifier is the operation name Safety Policies use (`safety-layer/README.md`).

| Operation | Identifier | Kind | Request (api-version at adoption) | Limits |
|---|---|---|---|---|
| Get work items | `get-work-items` | read | `GET _apis/wit/workitems` (7.1) | Items from other projects are dropped, after the whole batch is parsed: a malformed item from another project fails the call |
| Find work items | `find-work-items` | read | `POST _apis/wit/wiql` (7.1) | Built from structured filters; the agent never supplies WIQL; `[System.TeamProject] = @project` is always added; results are capped |
| Get work item comments | `get-work-item-comments` | read | `GET _apis/wit/workItems/{id}/comments` (7.1-preview.4) | Configured project only |
| Get wiki page | `get-wiki-page` | read | `GET _apis/wiki/wikis/{wikiIdentifier}/pages` (7.1) | Configured wikis only |
| Update work item | `update-work-item` | write, Safety Layer only | `PATCH _apis/wit/workitems/{id}` (7.1) | Integer id in the configured project; query string is `api-version` only; JSON Patch starts with a `test` on `/rev` from the preview read |

Only the operations implemented so far are on the allowlist in code; the rest of this table is the plan.
Adding one is a safety-critical PR, and adding the write operation is `Safety-Impact: loosens`.

Read volume is capped per call; the per-session cap is not implemented yet.
A write rejected because the revision changed fails closed and is shown to the user; it is never retried automatically.

## How the allowlist is enforced

`AllowlistTransport` wraps the httpx transport, so the check runs on the request as it is about to leave the process, after any code has built it.
It verifies the scheme, the host in the URL and the `Host` header, the organization, and the project, then matches the method and path against the allowlist and checks that every query parameter is listed and that `api-version` is the pinned one.
A client is constructed with one kind of operation, so read code cannot reach a write request even if one is added to the allowlist later.
Redirects are not followed: a redirect would send the request, and its credential, to an address nobody allowlisted.
Errors name the operation, the status code, or where a response failed validation; they never quote a response, since its content is untrusted.

| Module | Contents |
|---|---|
| `allowlist.py` | The allowlist and the transport that enforces it |
| `config.py` | The one organization and project the adapter talks to, and its token |
| `models.py` | Pydantic views of the responses; everything in them is untrusted data |
| `reads.py` | Read operations |

The adapter is async, because agent SDK tool calls are ([ADR 0004](../../docs/adr/0004-agent-runtime-port-with-claude-and-copilot-backends.md)), while the Safety Layer engine is synchronous deterministic code.
The write path therefore needs a seam between the two; it is designed with that step, not here.

## Credentials

- Token scopes: Work Items (Read & write) and Wiki (Read).
- Those scopes still allow changing state, assigning, and deleting work items, so the identity's project permissions must deny them (ARCHITECTURE.md §6); the Safety Layer is the inner boundary, not the only one.

## To be defined in Phase 1

- Which service account the token belongs to, and where it is stored. [ADR 0008](../../docs/adr/0008-sqlite-operational-store-and-a-service-account-per-system.md) decides that writes use one least-privilege service account per system, which resolves the question [ADR 0005](../../docs/adr/0005-azure-devops-adapter-calls-the-rest-api-directly.md) left open; where the credential lives is decided with hosting (ARCHITECTURE.md §11.1).
- How the token reaches `AzureDevOpsConfig`: it is passed in, and nothing here reads the environment yet.
- Pagination, retry, and rate-limit handling.
- The caps for query results, per-session reads, and response size.
