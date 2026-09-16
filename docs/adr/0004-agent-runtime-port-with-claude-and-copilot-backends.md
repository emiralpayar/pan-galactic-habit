# 0004. Agent runtime port with Claude and Copilot backends

- **Status:** Accepted
- **Date:** 2026-09-16
- **Deciders:** @emiralpayar

## Context

ARCHITECTURE.md §11 left the agent framework and the LLM provider open.
Two requirements shape the answer:

1. **Swappable backends.** Lobes must run on either Anthropic Claude or GitHub Copilot, chosen by committed configuration, without changes to lobe code, memory, or policy.
2. **A structural Tool Surface (§5.2).** The model must see only the lobe's allowlisted read tools and Safety Layer write tools — never an agent harness's built-in tools (shell, files, web) and never the raw tool list of an MCP server.

What the options look like as of September 2026:

- **Claude Agent SDK** (`claude-agent-sdk`, Python, 0.x) drives a bundled Claude Code CLI process with in-process custom tools.
  `tools=[]` disables every built-in tool, `setting_sources=[]` and `strict_mcp_config=True` ignore settings files and outside MCP configuration, and `permission_mode="dontAsk"` denies any tool that is not pre-approved.
  It authenticates with a Claude subscription token from `claude setup-token` (`CLAUDE_CODE_OAUTH_TOKEN`), an Anthropic API key, or a cloud provider account.
  Anthropic's help center (updated 2026-06-16) states that Agent SDK usage draws from the subscription's usage limits and that plan usage is per user.
  An earlier Anthropic legal notice (February 2026) said subscription tokens were not permitted in the Agent SDK, and a plan to meter programmatic usage separately at API rates is paused, not cancelled.
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
  The Orchestrator and Improver will use the same port; their tool sets are defined, under the same restrictions, when they are built (§12 steps 3–4).
  Only the Agent Runtime imports an agent SDK. An import-linter contract enforces this and also keeps the Safety Layer from importing the Agent Runtime.
- **Implement two backends** behind the port:
  - **Claude:** Claude Agent SDK with `tools=[]`, `setting_sources=[]`, `strict_mcp_config=True`, `permission_mode="dontAsk"`, and `allowed_tools` equal to the Tool Surface.
  - **Copilot:** GitHub Copilot SDK with `mode="empty"`, `available_tools` equal to the Tool Surface, and a permission handler that denies every request outside it.
- **Define each tool once** as a typed Python function with a Pydantic input model; each backend registers the same definitions in its SDK's format.
- **Keep MCP servers away from agent SDKs.** Adapters call MCP servers through the MCP Python client and expose only allowlisted operations as tools. No backend is given an MCP server configuration.
- **Verify the Tool Surface, not our configuration.** A contract test starts each backend with its production configuration and asserts that the tools offered to the model equal the Tool Surface exactly. A backend whose effective tool list cannot be verified is not enabled.
  The contract test runs for both backends on every PR that changes the Agent Runtime or its SDK pins; a lobe's Eval Suite runs on the backend and model committed for that lobe.
- **Pin both SDKs exactly** (`==`) in the Agent Runtime's `pyproject.toml`, so an SDK upgrade touches a safety-critical path and must pass the contract test.
- **Commit the choice, not the secrets.** The backend and model for each lobe are committed configuration, so changing either is a reviewed PR that runs the Eval Suite (§3: a deploy is a commit).
  Only credentials come from the environment or a secret manager.
- **Authenticate both backends with subscription tokens, not pay-as-you-go keys.**
  The Claude backend uses a Claude subscription token from `claude setup-token` (`CLAUDE_CODE_OAUTH_TOKEN`).
  The Copilot backend uses the GitHub token of an account with a Copilot plan, used only for Copilot and separate from the identities that push branches or open PRs.
  Tokens are personal: each developer and each deployment uses its own subscription, never another person's.
  An Anthropic API key, or a cloud provider's Claude endpoint once hosting is decided (§11), remains a fallback for the Claude backend without code changes.
- **Place the port and backends in a new top-level `agent-runtime/` component, classified safety-critical**, because a misconfigured backend bypasses the structural Tool Surface.
  The PR that adds its code also updates every file that lists safety-critical paths, commit scopes, or top-level components, including `scripts/checks/safety-critical-paths.txt`, `.github/CODEOWNERS`, `scripts/lib/conventions.sh`, ARCHITECTURE.md, AGENTS.md, CONTRIBUTING.md, and README.md.

## Consequences

- Lobes, and later the Orchestrator and Improver, depend on one small interface; switching a lobe's provider is a reviewed configuration change.
- An SDK release that silently adds a tool fails CI instead of reaching a deployment.
- We maintain two backends and their tests. Lobe code can use only features that the port exposes for both SDKs.
- Both SDKs are young and ship bundled CLI binaries; expect frequent upgrade PRs, each safety-critical.
- The container image must include both bundled CLIs, and the Copilot CLI must be shipped unmodified.
- CI and every deployment need a subscription token per backend, and usage counts against those subscriptions' limits.
- Anthropic's terms for subscription tokens in the Agent SDK have changed during 2026; if they change again, or programmatic usage moves to metered credits, the Claude backend switches to the API key fallback without a code change.
- How each SDK exposes the effective tool list for the contract test is settled in the PR that implements the backend.

## Alternatives considered

- **Microsoft Agent Framework.** One maintained interface over both SDKs.
  Not chosen: its Claude integration is beta and leaves built-in tools enabled by default, and it adds a layer we don't control in front of a safety-critical setting.
- **Pydantic AI or LiteLLM calling model APIs directly.** The simplest way to control the tool list.
  Not chosen: their Copilot providers imitate VS Code against an undocumented endpoint, which is not a supported integration and can break without notice.
- **Pay-as-you-go API keys by default.** Predictable terms and no per-user limits.
  Not chosen: the owners already hold Claude and Copilot subscriptions and both SDKs accept subscription tokens; API keys stay available as a fallback.
- **A single provider.** Simpler to build and test.
  Not chosen: it fails the swappable-backend requirement.
- **Giving the Azure DevOps MCP server to the agent SDK and filtering its tools there.** Less adapter code.
  Not chosen: safety would rest on SDK filtering, and the harness would receive the raw tool list, which §5.2 forbids.
