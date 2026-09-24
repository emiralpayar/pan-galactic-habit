# 0009. Claude backend refuses and neutralizes inherited environment

- **Status:** Accepted
- **Date:** 2026-09-21
- **Deciders:** @MGokcay

## Context

[ADR 0004](0004-agent-runtime-port-with-claude-and-copilot-backends.md) says the Agent Runtime "passes each SDK process an explicit environment instead of inheriting the parent's, and refuses to start if more than one Claude credential is present or an endpoint override is set that committed configuration does not name."

Implementing the Claude backend showed that `claude-agent-sdk` 0.2.157 cannot do the first half.
It always starts the CLI with the parent's environment (minus `CLAUDECODE`), then applies `ClaudeAgentOptions.env` on top: that option can add or override variables but never remove them.

The variables that matter are the ones that change which account, model, or endpoint a session uses: credentials, `ANTHROPIC_*`, cloud-provider switches, proxy and certificate settings, and loader variables.
The same implementation work also settled a question ADR 0004 left open: the CLI reports the tools it offers the model in its `init` message, before the first model turn.

## Decision

We will keep the intent of ADR 0004 (a session uses only the credential and endpoint that committed configuration and the person running it chose) and implement it as refuse and neutralize:

- **Refuse to start** when the parent environment holds more than one Claude credential, an `ANTHROPIC_BASE_URL` that configuration does not name, or a variable that matches one of:
  - a refused prefix (`ANTHROPIC_`, `BUN_`, `SSL_CERT_`, `CLAUDE_CODE_USE_`) — covers the SDK's own settings, the Bun runtime the CLI binary is built on, TLS trust, and every provider/gateway switch without naming each one;
  - a `CLAUDE_CODE_*` name containing `TOKEN`, `KEY`, `CRED`, `PROXY`, `CERT`, `BASE_URL`, or `OAUTH_URL` — covers the CLI's own credential, proxy, certificate, and endpoint variables, found by reading the pinned CLI binary rather than its (undocumented) source;
  - a short named list for everything else that changes what the CLI loads or trusts (loader variables, `NODE_TLS_REJECT_UNAUTHORIZED`, the SDK's version-check bypass).
- **Neutralize** what the backend does not use by overriding it with an empty value in the environment it passes, and point the CLI at an empty settings directory and turn its self-update off.
- **Read the tool list from the `init` message.** The Tool Surface contract test and every session compare it with the Tool Surface exactly, compare the reported MCP servers with the one in-process server, and compare the reported `apiKeySource` with the credential the backend actually handed the CLI (or `"none"`).

The refused prefixes, substrings, and named list are a deny-list, so they have to grow when the SDK or CLI gains a new way to redirect a session.
A change to the SDK pin is therefore reviewed for new such variables, as it already is for the contract test.

## Consequences

- A developer or runner with a proxy, model override, or provider switch set gets a clear refusal instead of a silently different session. Committed configuration can name a permitted value later.
- Variables that are not listed still reach the CLI process. With `tools=[]` the model cannot use them (for example `GITHUB_TOKEN` or `AZURE_DEVOPS_PAT`), so the exposure is limited to the CLI process itself.
- Whether the CLI treats an empty value as unset is assumed, not tested.
- The `apiKeySource` the CLI reports for `ANTHROPIC_API_KEY` and for no credential is confirmed against the pinned binary; the value for a real `CLAUDE_CODE_OAUTH_TOKEN` is not yet, since that needs a real token. If it turns out not to equal the variable name, every OAuth session fails closed at the `_check_init` comparison rather than silently, so this is safe to leave open, not something that must block a merge on its own.
- A true explicit environment needs a custom transport or a launcher for the CLI; revisit that if the SDK adds support or the deny-list proves hard to maintain.
- The Copilot backend has to make the same decision for its SDK.

## Alternatives considered

- **A wrapper launcher (`env -i …`) as the CLI path.** A real explicit environment. Not chosen for now: it adds a script to a safety-critical component, and the contract test would have to cover it.
- **Scrubbing `os.environ` in process while the SDK starts.** Fragile and racy in an async application.
- **Inheriting silently.** Rejected: it contradicts the intent of ADR 0004.
