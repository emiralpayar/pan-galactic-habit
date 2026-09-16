# 0005. Azure DevOps adapter calls the REST API directly

- **Status:** Accepted
- **Date:** 2026-09-16
- **Deciders:** @emiralpayar

## Context

ARCHITECTURE.md §6 planned to integrate Azure DevOps through the official Microsoft MCP server, pinned and limited to the `work-items`, `work`, and `wiki` domains.
[ADR 0004](0004-agent-runtime-port-with-claude-and-copilot-backends.md) then ruled that no MCP server is ever handed to an agent: adapters call their integrations themselves and expose only allowlisted operations as tools.
Reviewing that decision in #5, @mgokcay asked whether MCP still earns its place under that rule, or whether adapters should call the API directly.

The forces at play:

- **Payload-level policy checks (§5.2).** The Safety Layer must validate the write that actually reaches the external system.
  Through MCP, the adapter sends tool arguments and the MCP server builds the HTTP request, so the validated payload is not the payload sent.
- **Execution-time re-validation (§5.2).** A confirmed write must not land on a work item that changed after the user saw the diff.
- **Tool list churn.** The local MCP server (`@azure-devops/mcp` 2.10.0) has no read-only mode: enabling `work-items` exposes its write tools, and each upgrade can add tools that must be classified.
- **Runtime footprint.** The MCP server is the only component that would need Node.js at runtime.
- **Scope.** Phase 1 needs few operations: read work items, run a WIQL query, read work item comments, read a wiki page, and update fields with JSON Patch.
- **Clients.** Microsoft's Python package, `azure-devops`, has been a beta (7.1.0b4) since November 2023; the maintained official client is the Node.js `azure-devops-node-api`.

## Decision

We will:

- **Implement the Azure DevOps adapter over the REST API** with `httpx` and Pydantic models for the responses we use.
  Every endpoint is pinned to an explicit `api-version`: 7.1 where it is generally available, and `7.1-preview.4` for work item comments.
  Changing a pinned version is a safety-critical PR.
- **Allowlist operations in code.** The adapter exposes read operations for work items, WIQL queries, work item comments, and wiki pages, and one write operation, a JSON Patch update of a work item, which only the Safety Layer can call.
  No other endpoint is reachable.
- **Send exactly what the Safety Layer validated.** The write request body is the validated JSON Patch, unchanged.
  That patch starts with a `test` operation on `/rev` carrying the revision shown in the diff preview, so Azure DevOps rejects the write if the work item changed after the user confirmed it.
- **Keep MCP as an option for other systems.** An adapter may wrap an MCP server when that is the better integration.
  It still classifies every server tool, pins the server version, and never exposes the server to an agent (ADR 0004).
- **Leave the credential model open.** The adapter reads credentials from the environment or a secret manager; whether writes run under a service account or the confirming user stays an open question (§11).

## Consequences

- The Safety Layer validates the exact request body Azure DevOps receives, and stale confirmations fail at the API instead of overwriting newer edits.
- The tool surface changes only when our code changes, never with an upstream release.
- Node.js is no longer needed at runtime; development still uses it for markdownlint.
- We write and maintain the HTTP calls, pagination, retries, and error mapping ourselves, and follow Azure DevOps API version retirements.
- The comments endpoint is a preview version and may change; it is pinned and covered by adapter tests.
- Each new Azure DevOps capability is adapter code in a safety-critical PR, not a configuration switch.

## Alternatives considered

- **The official Azure DevOps MCP server behind the adapter** (the original plan). Maintained by Microsoft, broad coverage, less code.
  Not chosen: the Safety Layer would not see the real request, upgrades change the tool list, and since agents never use its tools directly, its breadth goes unused.
- **The hosted Azure DevOps MCP server.** Offers read-only and toolset filters.
  Not chosen: it is in preview, supports only Entra ID with a custom app registration for non-Microsoft clients, and still hides the real request from the Safety Layer.
- **The `azure-devops` Python package.** Generated typed clients for every area.
  Not chosen: it has been in beta since 2023 and hides the request body behind generated models.
- **TypeScript, for the maintained `azure-devops-node-api` client.**
  Not chosen: the adapter needs a handful of endpoints, and the reasons for Python in [ADR 0003](0003-use-python-as-the-implementation-language.md) outweigh a client library.
