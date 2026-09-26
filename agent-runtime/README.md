# Agent Runtime

> **Status:** in progress — Phase 1. The port and the Claude backend exist, with read-only tools; the Copilot backend and the habit-facing tool wiring do not. **Safety-critical.** Every change requires a `Safety-Impact` declaration and code owner approval.

The port habits run agent sessions through, and the backends behind it ([ADR 0004](../docs/adr/0004-agent-runtime-port-with-claude-and-copilot-backends.md), ARCHITECTURE.md §5.2).
A session is a habit's instructions (memory), a **Tool Surface**, and a conversation.
The model sees the Tool Surface and nothing else: no shell, files, web, or external MCP server.

## Responsibilities

- Define the `AgentRuntime` port and the typed tool definitions (`Tool`, `ToolSurface`).
- Configure each backend so its effective tool list equals the Tool Surface, and check that at the start of every session.
- Refuse and neutralize the parent environment ([ADR 0009](../docs/adr/0009-claude-backend-refuses-and-neutralizes-inherited-environment.md)): exactly one supported credential, no other `ANTHROPIC_*`, proxy, or provider variable, no unnamed endpoint override, and no access to the user's own Claude settings.
- Pin the SDK and CLI runtime versions exactly, and fetch nothing at runtime.

It does **not** decide what a tool may do. Tools that read are ungated but untrusted; writes are never a tool and go through the Safety Layer.

## Invariants

These must hold for every change to this component, and must be covered by tests:

1. **Structural Tool Surface.** The tools offered to the model equal the request's Tool Surface exactly. A backend whose effective tool list cannot be read is not enabled.
2. **Fail before the model acts.** A mismatch raises `ToolSurfaceError` before any model output is used.
3. **One SDK, one place.** Only this component imports an agent SDK (import contracts in the root `pyproject.toml`); it imports no adapter and no Safety Layer code.
4. **No ambiguous credentials or endpoints.** More than one Claude credential, an unsupported authentication, provider, proxy, or model variable, or an endpoint override the committed configuration does not name is refused.
5. **Nothing fetched at runtime.** The CLI runtime is the one installed with the pinned SDK.

## Claude backend

Claude Agent SDK, configured with `tools=[]`, `setting_sources=[]`, `strict_mcp_config=True`, `permission_mode="dontAsk"`, and `allowed_tools` equal to the Tool Surface.
Tools are registered through an in-process MCP server, so the model sees them as `mcp__habit__<name>`; the backend maps names back.

The SDK merges the environment it is given onto the parent's and cannot remove variables from it (ADR 0009).
The backend therefore refuses to start when the parent sets an ambiguous or unsupported variable, and overrides the credentials and endpoint it does not use with an empty value.
The refused list is a deny-list: an SDK or CLI upgrade is reviewed for new variables that redirect a session.
The CLI reads its settings from an empty temporary directory, not the user's, and its self-update is off.

## Tool Surface contract test

`tests/test_tool_surface_contract.py` starts each backend with its production configuration and the installed CLI runtime, and compares the tools it reports with the Tool Surface.
The CLI reports its tool list and MCP servers in its `init` message, before the first model turn, so the test needs no credential and runs without calling a model. `effective_tools` sends a placeholder prompt to get that message, so with a credential set a model call may already have started when it interrupts: run it without one.
A companion test enables the SDK's built-in tools and checks that the report shows them, so the contract cannot pass by reading nothing.
New backends add themselves to `BACKENDS` in that test.

## Change rules

- Changing the SDK or CLI pin, or any option that affects the tool list, must pass the contract test and is `Safety-Impact: neutral` only if the effective tool list is unchanged.
- Adding a tool to a habit's Tool Surface belongs to the habit, not here; a tool that writes to an external system does not belong on a Tool Surface at all. This is not enforced in code: the handler is arbitrary Python, so habit and adapter reviews own it.
- The import contract that confines agent SDKs covers the packages that exist; add each new Python package (habits, orchestrator, improver, interface) to it when it is created.
