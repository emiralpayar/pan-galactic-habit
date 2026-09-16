# 0003. Use Python as the implementation language

- **Status:** Accepted
- **Date:** 2026-09-16
- **Deciders:** @emiralpayar

## Context

ARCHITECTURE.md §11 left the implementation language open.
Nothing in Phase 1 (§12) can be built until it is chosen: the Safety Layer engine, the Azure DevOps adapter, the Backlog Refiner agent, the chat interface, and the eval harness all depend on it.

The forces at play:

- Lobes must run on either the Claude Agent SDK or the GitHub Copilot SDK ([ADR 0004](0004-agent-runtime-port-with-claude-and-copilot-backends.md)).
  The Claude Agent SDK exists only for Python and TypeScript; the Copilot SDK exists for both of those and several other languages.
- The Azure DevOps MCP server is a Node.js program that runs as a separate process over stdio.
  It needs Node.js 20 or later at runtime whatever language the client is written in.
- The Safety Layer must validate declarative policy files and write payloads deterministically, and prove its invariants with tests (`safety-layer/README.md`).
- The boundary check in §4.2 must fail CI when lobe code imports adapter write internals, which needs import-level enforcement.
- Many authors are AI agents, so standards must be enforced by tools rather than by convention.

## Decision

We will implement the system in **Python 3**, starting with 3.13, with the following standards:

| Concern | Standard |
|---|---|
| Interpreter and dependencies | uv. `.python-version` pins the exact Python version (3.13 at adoption); a committed `uv.lock` pins every dependency exactly. |
| Project layout | One uv workspace at the repository root. Each component (e.g. `safety-layer/core`, `adapters/azure-devops`, `lobes/backlog-refiner/agent`) is a workspace member with its own `pyproject.toml` and a `src/` layout. A lobe's memory, policy, and evals stay data files outside the package. Directories stay kebab-case; import packages use the snake_case equivalent. |
| Lint and format | ruff (`ruff check`, `ruff format`) |
| Type checking | mypy `--strict` |
| Tests | pytest |
| Validation at trust boundaries | Pydantic models for policy files, tool inputs, and data read from external systems |
| Boundary check (§4.2) | import-linter contracts |

The first PR that adds Python code also adds CI jobs for these tools, adds those jobs to the required status checks in `.github/rulesets/protect-main.json`, and adds a `uv` entry to `.github/dependabot.yml`.
That PR is safety-critical because it changes CI and the ruleset.

## Consequences

- Phase 1 can start.
- Both agent backends chosen in ADR 0004 have first-party Python SDKs.
- The §4.2 boundary check becomes implementable with an existing tool instead of custom scripts.
- Development environments and the container image need two runtimes: Python for the system and Node.js for the Azure DevOps MCP server.
- Python types are not enforced at runtime; mypy `--strict` in CI and Pydantic at trust boundaries compensate.
- Adding CI jobs later means updating the ruleset's required checks in the same PR (ADR 0002).

## Alternatives considered

- **TypeScript.** One runtime for the system and the MCP server, and both agent SDKs support it.
  Not chosen: the MCP server runs as a separate process either way, and Python gives us Pydantic for policy validation, import-linter for the boundary check, and a broader ecosystem for evals and the data analysis the Improver will need.
- **Python 3.14.** Newer, with a longer support window.
  Not chosen as the starting version: 3.13 is the safer choice for dependency compatibility.
  Upgrading later stays within this decision: a normal PR changes `.python-version` and every other place the version appears (`requires-python`, tool target versions, the container base image).
- **Go, .NET, Java, or Rust.** The GitHub Copilot SDK supports them.
  Not chosen: the Claude Agent SDK does not, which breaks the swappable-backend requirement.
