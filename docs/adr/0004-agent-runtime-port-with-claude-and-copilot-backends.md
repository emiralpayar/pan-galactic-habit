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

- **Claude Agent SDK** (`claude-agent-sdk`, Python, 0.x) drives a Claude Code CLI binary shipped inside the package, with in-process custom tools.
  `tools=[]` disables every built-in tool, `setting_sources=[]` and `strict_mcp_config=True` ignore settings files and outside MCP configuration, and `permission_mode="dontAsk"` denies any tool that is not pre-approved.
  It authenticates with a Claude subscription token from `claude setup-token` (`CLAUDE_CODE_OAUTH_TOKEN`, valid for about a year), an Anthropic API key, or a cloud provider account.
  Anthropic's help center (updated 2026-06-16) states that Agent SDK usage draws from the subscription's usage limits and that plan usage is per user.
  An earlier Anthropic legal notice (February 2026) said subscription tokens were not permitted in the Agent SDK, and a plan to meter programmatic usage separately at API rates is paused, not cancelled.
- **GitHub Copilot SDK** (`github-copilot-sdk`, Python, generally available since June 2026) drives the Copilot CLI over JSON-RPC.
  The Python package does not contain the CLI: unless `COPILOT_SKIP_CLI_DOWNLOAD` is set and `COPILOT_CLI_PATH` names an installed runtime, it downloads the runtime from GitHub Releases on first use.
  `mode="empty"` refuses to start a session without `available_tools`, an allowlist over built-in, MCP, and custom tools.
  It authenticates with a GitHub token (a fine-grained token needs only the Copilot Requests permission), bills usage to that user's Copilot plan, and also offers Claude models.
  The CLI is proprietary and may be redistributed only unmodified.
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
- **Keep MCP servers away from agent SDKs.** An adapter that uses an MCP server calls it through the MCP Python client and exposes only allowlisted operations as tools; the Azure DevOps adapter calls its REST API directly ([ADR 0005](0005-azure-devops-adapter-calls-the-rest-api-directly.md)). No backend is given an MCP server configuration.
- **Verify the Tool Surface, not our configuration.** A contract test starts each backend with its production configuration and installed runtime, and asserts that the tools offered to the model equal the Tool Surface exactly. A backend whose effective tool list cannot be verified is not enabled.
  The contract test runs for both backends on every PR that changes the Agent Runtime or its pins; a lobe's Eval Suite runs on the backend and model committed for that lobe.
- **Pin both SDKs and both CLI runtimes exactly.** The SDKs are pinned with `==` in the Agent Runtime's `pyproject.toml`; the Copilot CLI runtime version is pinned in the same component.
  Any change to these pins touches a safety-critical path and must pass the contract test.
- **Fetch nothing at runtime.** The build installs both CLI runtimes from their official release packages, unmodified.
  At runtime the Agent Runtime sets `COPILOT_SKIP_CLI_DOWNLOAD=1` and an explicit CLI path, so a deployment runs exactly what its commit built (§3, §4.4).
- **Commit the choice, not the secrets.** The backend, model, and any non-default model endpoint for each lobe are committed configuration, so changing any of them is a reviewed PR that runs the Eval Suite.
  Only credentials come from the environment or a secret manager.
- **Hand each SDK only its own credentials, and refuse ambiguity.** The Agent Runtime passes each SDK process an explicit environment instead of inheriting the parent's, and refuses to start if more than one Claude credential is present or an endpoint override is set that committed configuration does not name.
- **Use personal subscription tokens for single-user runs.**
  - The Claude backend uses the running person's subscription token from `claude setup-token`.
  - The Copilot backend uses the running person's fine-grained token with only the Copilot Requests permission and no repository access, separate from the tokens that push branches or open PRs.
  - Single-user runs are local development and a lobe operated by the token's owner for their own work, which covers the Phase 1 exit criteria.
  - Tokens are never shared: a person's token only runs sessions that person starts or approves.
  - An Anthropic API key is the only credential the environment may use instead of a Claude subscription token.
- **Gate CI runs that need model credentials.** Jobs that call a model (the contract test and evals) run in a GitHub Environment whose secrets belong to one person and whose runs that person must approve; unapproved runs, including Dependabot and bot-authored PRs, never receive them.
- **Leave shared credentials open.** Credentials for a deployment that serves several people, and for the Orchestrator and Improver identities, are an open question (§11) to be decided with hosting and user authentication.
- **Place the port and backends in a new top-level `agent-runtime/` component, classified safety-critical**, because a misconfigured backend bypasses the structural Tool Surface.
  The PR that adds its code also updates every file that lists safety-critical paths, commit scopes, or top-level components, including `scripts/checks/safety-critical-paths.txt`, `.github/CODEOWNERS`, `scripts/lib/conventions.sh`, ARCHITECTURE.md, AGENTS.md, CONTRIBUTING.md, and README.md.

## Consequences

- Lobes, and later the Orchestrator and Improver, depend on one small interface; switching a lobe's provider is a reviewed configuration change.
- An SDK or CLI release that silently adds a tool fails CI instead of reaching a deployment.
- We maintain two backends and their tests. Lobe code can use only features that the port exposes for both SDKs.
- Both SDKs and CLIs are young; expect frequent upgrade PRs, each safety-critical.
- The container image carries both CLI runtimes, installed unmodified at build time.
- Usage counts against the approving person's subscription limits; subscription tokens expire (about a year for `claude setup-token`) and must be rotated.
- Anthropic's terms for subscription tokens in the Agent SDK changed during 2026; if they change again, or programmatic usage moves to metered credits, single-user runs switch to an Anthropic API key without a code change.
- A deployment that serves several people cannot go live until the shared-credential question in §11 is decided.
- How each SDK exposes the effective tool list for the contract test is settled in the PR that implements the backend.

## Alternatives considered

- **Microsoft Agent Framework.** One maintained interface over both SDKs.
  Not chosen: its Claude integration is beta and leaves built-in tools enabled by default, and it adds a layer we don't control in front of a safety-critical setting.
- **Pydantic AI or LiteLLM calling model APIs directly.** The simplest way to control the tool list.
  Not chosen: their Copilot providers imitate VS Code against an undocumented endpoint, which is not a supported integration and can break without notice.
- **Pay-as-you-go API keys by default.** Predictable terms, no per-person limits, and suitable for shared deployments.
  Not chosen for single-user runs: the owners already hold Claude and Copilot subscriptions and both SDKs accept subscription tokens. API keys remain the Claude fallback and a candidate for the shared-credential question.
- **A single provider.** Simpler to build and test.
  Not chosen: it fails the swappable-backend requirement.
- **Giving the Azure DevOps MCP server to the agent SDK and filtering its tools there.** Less adapter code.
  Not chosen: safety would rest on SDK filtering, and the harness would receive the raw tool list, which §5.2 forbids.
