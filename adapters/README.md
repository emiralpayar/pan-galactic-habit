# Adapters

> **Safety-critical.** Every change under `adapters/` requires a `Safety-Impact` declaration and code owner approval.

An adapter is the system-specific integration layer between lobes and one external system (ARCHITECTURE.md §2, §5.2). Adapters are shared by all lobes that use the same system.

## Responsibilities

- **Classify every operation** the adapter exposes as `read` or `write`; nothing else in the external system is reachable. An adapter that wraps an MCP server classifies every server tool, and **unclassified tools are unavailable.**
- **Expose read tools** directly to agents — their results are marked as untrusted.
- **Expose write capabilities only to the Safety Layer**, never to agent code.
- **Pin the external integration version** (the REST `api-version`, or the MCP server version). Changing it is a PR that shows the tool surface diff.
- Translate approved writes into the external system's API.

## Rules for changes

- A new tool classified as `write`, or any tool reclassified from `write` to `read`, is `Safety-Impact: loosens`.
- Adapter code must not contain lobe-specific rules; those belong in the lobe's policy.
- Credentials are least-privilege and come from the environment or a secret manager — never from code or config in git.
- Tests must cover the classification: an unknown tool must be rejected.

## Adapters

| Adapter | System | Integration | Status |
|---|---|---|---|
| [azure-devops](azure-devops/) | Azure DevOps | REST API, pinned `api-version` ([ADR 0005](../docs/adr/0005-azure-devops-adapter-calls-the-rest-api-directly.md)) | Not started (Phase 1) |
