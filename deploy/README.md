# Deploy

> **Status:** not started. The Dockerfile and deploy workflow arrive after hosting is decided (ARCHITECTURE.md §11). The image will need Python ([ADR 0003](../docs/adr/0003-use-python-as-the-implementation-language.md)), Node.js 20 or later for the Azure DevOps MCP server, and the CLIs bundled with the agent SDKs, shipped unmodified ([ADR 0004](../docs/adr/0004-agent-runtime-port-with-claude-and-copilot-backends.md)).

Builds the stateless container image and deploys it (ARCHITECTURE.md §4.4).

## Requirements

- The image bakes in the repository contents at one commit and is tagged with that commit SHA.
- The container never fetches code or memory from git at runtime.
- No secrets in the image; they are injected at runtime from a secret manager.
- Rolling back means redeploying an earlier SHA.
