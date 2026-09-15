# Azure DevOps Adapter

> **Status:** not started — Phase 1. **Safety-critical.**

Integrates Azure DevOps through the official Microsoft Azure DevOps MCP server, limited to the `work-items`, `work`, and `wiki` domains (ARCHITECTURE.md §6).

## To be defined in Phase 1

- The pinned MCP server version.
- The read/write classification of every tool in the enabled domains.
- The credential model and minimum permission scopes (see ARCHITECTURE.md §11, write identity).
- How approved writes are translated into work item updates (e.g. JSON Patch operations) so the Safety Layer can validate the payload.
