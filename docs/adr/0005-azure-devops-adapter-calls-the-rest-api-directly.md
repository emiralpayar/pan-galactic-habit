# 0005. Azure DevOps adapter calls the REST API directly

- **Status:** Accepted
- **Date:** 2026-09-16
- **Deciders:** @emiralpayar

## Context

ARCHITECTURE.md §6 planned to integrate Azure DevOps through the official Microsoft MCP server, pinned and limited to the `work-items`, `work`, and `wiki` domains.
[ADR 0004](0004-agent-runtime-port-with-claude-and-copilot-backends.md) then ruled that no MCP server is ever handed to an agent: adapters call their integrations themselves and expose only allowlisted operations as tools.
Reviewing that decision in #5, @mgokcay asked whether MCP still earns its place under that rule, or whether adapters should call the API directly.

The forces at play:

- **Payload-level policy checks (§5.2).** The Safety Layer must validate the write that actually reaches the external system — its target and parameters as well as its body.
  Through MCP, the adapter sends tool arguments and the MCP server builds the HTTP request, so the validated write is not the write sent.
- **Execution-time re-validation (§5.2).** A confirmed write must not land on a work item that changed after the user saw the diff.
- **Untrusted input (§5.3).** Content read from work items can steer the agent's next read, so reads must not reach beyond the configured project.
- **Tool list churn.** The local MCP server (`@azure-devops/mcp` 2.10.0) has no read-only mode: enabling `work-items` exposes its write tools, and each upgrade can add tools that must be classified.
- **Runtime footprint.** The MCP server is the only component that would need Node.js at runtime.
- **Scope.** Phase 1 needs few operations: read work items, find backlog items, read work item comments, read a wiki page, and update fields.
- **Clients.** Microsoft's Python package, `azure-devops`, has been a beta (7.1.0b4) since November 2023; the maintained official client is the Node.js `azure-devops-node-api`.

## Decision

We will:

- **Implement the Azure DevOps adapter over the REST API** with `httpx`, which the GitHub Copilot SDK already depends on, and Pydantic models for the responses we use.
  `httpx` is pinned with `==` in the adapter's `pyproject.toml`.
  Every endpoint is pinned to an explicit `api-version` (7.1 at adoption, and a preview version where no generally available one exists, such as work item comments).
  Changing a pinned version stays within this decision and is a safety-critical PR that links the API's change notes for the affected endpoints.
- **Allowlist requests, not just operations.** The adapter can send only requests whose method, path template, and query parameters are on its allowlist; anything else is rejected before it is sent.
  The allowlist covers reads of work items, backlog queries, work item comments, and wiki pages, and one write, a JSON Patch update of a work item that only the Safety Layer can call.
  The old MCP `work` domain is not needed: backlog items are found with WIQL.
- **Keep reads inside the configured project.**
  - The agent never supplies raw WIQL. The adapter builds each query from structured filters, always adds `[System.TeamProject] = @project`, and caps the result count.
  - Work items and comments from any other project are dropped.
  - Wiki reads are limited to the configured wikis.
  - Read volume is capped per call and per session.
- **Build the whole write request in trusted code, then validate all of it.**
  - The agent proposes field values only.
  - The adapter builds the request: `PATCH` to the configured organization and project, an integer work item id, a query string containing only `api-version`, and a JSON Patch body.
  - The body starts with a `test` operation on `/rev`, using the revision from the same read that produced the diff preview. The agent never supplies it.
  - The Safety Layer validates the complete request: `test` operations are allowed as non-mutating preconditions, `move` and `copy` are rejected, and every other operation must target an allowlisted field.
  - The diff preview shows the project, work item id, and revision.
  - `bypassRules`, `suppressNotifications`, and every other query parameter are never sent.
- **Send exactly what was validated.** The adapter sends the validated request unchanged.
  If Azure DevOps rejects the write because the revision changed, the write fails closed and the user is told; it is never retried automatically with a newer revision.
- **Limit MCP to reads.** An adapter for another system may wrap an MCP server for reads, provided it classifies every server tool, fails at startup if the server's tool list differs from the classified set, pins the server version inside its own directory, and never exposes the server to an agent (ADR 0004).
  An MCP-backed write needs a new ADR showing how it meets §5.2.
- **Keep HTTP clients out of lobe code.** An import-linter contract stops lobe code from importing `httpx`, so lobes reach Azure DevOps only through the adapter's tools.
- **Leave the credential model open.** The adapter reads credentials from the environment or a secret manager.
  Its token needs only the Work Items (Read & write) and Wiki (Read) scopes, but those scopes still allow state changes and deletion, so the identity's project permissions must deny them.
  Whether writes run under a service account or the confirming user stays an open question (§11).

## Consequences

- The Safety Layer validates the exact request Azure DevOps receives, and stale confirmations fail at the API instead of overwriting newer edits.
- The tool surface changes only when our code changes, never with an upstream release.
- Node.js is no longer needed at runtime; development still uses it for markdownlint.
- We write and maintain the HTTP calls, query building, pagination, retries, and error mapping ourselves, and follow Azure DevOps API version retirements.
- The comments endpoint is a preview version and may change; it is pinned and covered by adapter tests.
- Reads are narrower than the API allows, so some agent requests will be refused and need a reviewed adapter change instead.
- Each new Azure DevOps capability is adapter code in a safety-critical PR, not a configuration switch.

## Alternatives considered

- **The official Azure DevOps MCP server behind the adapter** (the original plan). Maintained by Microsoft, broad coverage, less code.
  Not chosen: the Safety Layer would not see the real request, upgrades change the tool list, and since agents never use its tools directly, its breadth goes unused.
- **The hosted Azure DevOps MCP server.** Offers read-only and toolset filters.
  Not chosen: it is in preview, supports only Entra ID with a custom app registration for non-Microsoft clients, and still hides the real request from the Safety Layer.
- **The `azure-devops` Python package.** Generated typed clients for every area.
  Not chosen: it has been in beta since 2023 and hides the request behind generated models.
- **TypeScript, for the maintained `azure-devops-node-api` client.**
  Not chosen: the adapter needs a handful of endpoints, and the reasons for Python in [ADR 0003](0003-use-python-as-the-implementation-language.md) outweigh a client library.
- **Letting the agent write WIQL.** More flexible queries.
  Not chosen: injected content could steer queries across projects or into very large result sets.
