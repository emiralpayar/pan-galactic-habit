# Adapters

> **Safety-critical.** Every change under `adapters/` requires a `Safety-Impact` declaration and code owner approval.

An adapter is the system-specific integration layer between lobes and one external system (ARCHITECTURE.md §2, §5.2). Adapters are shared by all lobes that use the same system.

## Responsibilities

- **Allowlist every request** the adapter can send (method, path template, query parameters) and classify each operation as `read` or `write`; **nothing else in the external system is reachable.** An adapter may wrap an MCP server for reads only: it classifies every server tool, fails at startup if the server's tool list differs from the classified set, and never exposes the server to an agent.
- **Expose read tools** directly to agents — their results are marked as untrusted.
- **Expose write capabilities only to the Safety Layer**, never to agent code.
- **Pin the external integration version** (the REST `api-version`, or the MCP server version) inside the adapter's own directory, so the safety guard detects a change. A REST version change links the API's change notes for the affected endpoints; an MCP server upgrade shows the tool list diff.
- Translate approved writes into the external system's API.

## Rules for changes

- A new write operation or MCP tool classified as `write`, or any reclassification from `write` to `read`, is `Safety-Impact: loosens`.
- Adapter code must not contain lobe-specific rules; those belong in the lobe's policy.
- Credentials are least-privilege and come from the environment or a secret manager — never from code or config in git.
- Tests must cover the allowlist: a request outside it (method, path template, query parameters, `api-version`) or an unknown MCP tool must be rejected.

## Adapters

| Adapter | System | Integration | Status |
|---|---|---|---|
| [azure-devops](azure-devops/) | Azure DevOps | REST API, pinned `api-version` ([ADR 0005](../docs/adr/0005-azure-devops-adapter-calls-the-rest-api-directly.md)) | Not started (Phase 1) |
