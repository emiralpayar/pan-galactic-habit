# 0004. Agent runtime port with Claude and Copilot backends

- **Status:** Accepted
- **Date:** 2026-09-16
- **Deciders:** @emiralpayar

## Context

ARCHITECTURE.md §11 left the agent framework and the LLM provider open.
Two requirements shape the answer:

1. **Swappable backends.** Lobes must run on either Anthropic Claude or GitHub Copilot, chosen by configuration, without changes to lobe code, memory, or policy.
2. **A structural Tool Surface (§5.2).** The model must see only the lobe's allowlisted read tools and Safety Layer write tools — never an agent harness's built-in tools (shell, files, web) and never the raw tool list of an MCP server.

What the options look like as of September 2026:

- **Claude Agent SDK** (`claude-agent-sdk`, Python, 0.x) drives a bundled Claude Code CLI process with in-process custom tools.
  `tools=[]` disables every built-in tool, `setting_sources=[]` and `strict_mcp_config=True` ignore settings files and outside MCP configuration, and `permission_mode="dontAsk"` denies any tool that is not pre-approved.
  It requires an Anthropic API key or a cloud provider account; consumer subscription logins are not permitted for this use.
- **GitHub Copilot SDK** (`github-copilot-sdk`, Python, generally available since June 2026) drives a bundled Copilot CLI over JSON-RPC.
  `mode="empty"` refuses to start a session without `available_tools`, an allowlist over built-in, MCP, and custom tools.
  It authenticates with a GitHub token, bills usage to a Copilot plan, and also offers Claude models.
  The bundled CLI is proprietary and may be redistributed only unmodified.
- **Microsoft Agent Framework** wraps both SDKs behind one interface, but its Claude integration is in beta and keeps the CLI's built-in tools unless extra untyped options are passed, and its Copilot integration pins an older SDK version.
- **Pydantic AI and LiteLLM** reach Copilot by presenting themselves as VS Code to an undocumented endpoint.
  GitHub Models, the documented model API, was retired on 2026-07-30.
- The **Azure DevOps MCP server** has no read-only mode when run locally: enabling the work-items domain also exposes its write tools.

## Decision

We will:

- **Define an `AgentRuntime` port** in this repository.
  Lobe code runs a session through it by passing instructions (memory), the Tool Surface, and the conversation.
  Lobe code never imports an agent SDK.
- **Implement two backends** behind the port, selected by configuration:
  - **Claude:** Claude Agent SDK with `tools=[]`, `setting_sources=[]`, `strict_mcp_config=True`, `permission_mode="dontAsk"`, and `allowed_tools` equal to the Tool Surface.
  - **Copilot:** GitHub Copilot SDK with `mode="empty"`, `available_tools` equal to the Tool Surface, and a permission handler that denies every request outside it.
- **Define each tool once** as a typed Python function with a Pydantic input model; each backend registers the same definitions in its SDK's format.
- **Keep MCP servers away from agent SDKs.** Adapters call MCP servers through the MCP Python client and expose only allowlisted operations as tools. No backend is given an MCP server configuration.
- **Verify the Tool Surface, not our configuration.** A contract test starts each backend with its production configuration and asserts that the tools offered to the model equal the Tool Surface exactly. A backend whose effective tool list cannot be verified is not enabled.
- **Pin both SDKs exactly.** An SDK upgrade is a PR that must pass the contract test.
- **Keep models and credentials out of code.** Model names are configuration. The Claude backend uses an Anthropic API key; the Copilot backend uses a GitHub token for an account with a Copilot plan. Both come from the environment or a secret manager.
- **Place the port and backends in a new top-level `agent-runtime/` component, classified safety-critical**, because a misconfigured backend bypasses the structural Tool Surface.
  The PR that adds its code also adds it to `scripts/checks/safety-critical-paths.txt`, `.github/CODEOWNERS`, ARCHITECTURE.md §9, and the commit scopes.

## Consequences

- Lobes, and later the Orchestrator and Improver, depend on one small interface; switching provider is a configuration change.
- An SDK release that silently adds a tool fails CI instead of reaching a deployment.
- We maintain two backends and their tests. Lobe code can use only features that the port exposes for both SDKs.
- Both SDKs are young and ship bundled CLI binaries; expect frequent upgrade PRs, each safety-critical.
- The container image must include both bundled CLIs, and the Copilot CLI must be shipped unmodified.
- Running evals on both backends in CI needs credentials for both and incurs usage costs on both.
- How each SDK exposes the effective tool list for the contract test is settled in the PR that implements the backend.

## Alternatives considered

- **Microsoft Agent Framework.** One maintained interface over both SDKs.
  Not chosen: its Claude integration is beta and leaves built-in tools enabled by default, and it adds a layer we don't control in front of a safety-critical setting.
- **Pydantic AI or LiteLLM calling model APIs directly.** The simplest way to control the tool list.
  Not chosen: their Copilot providers imitate VS Code against an undocumented endpoint, which is not a supported integration and can break without notice.
- **A single provider.** Simpler to build and test.
  Not chosen: it fails the swappable-backend requirement.
- **Giving the Azure DevOps MCP server to the agent SDK and filtering its tools there.** Less adapter code.
  Not chosen: safety would rest on SDK filtering, and the harness would receive the raw tool list, which §5.2 forbids.
