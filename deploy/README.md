# Deploy

> **Status:** not started. The Dockerfile and deploy workflow arrive after the implementation language and hosting are decided (ARCHITECTURE.md §11).

Builds the stateless container image and deploys it (ARCHITECTURE.md §4.4).

## Requirements

- The image bakes in the repository contents at one commit and is tagged with that commit SHA.
- The container never fetches code or memory from git at runtime.
- No secrets in the image; they are injected at runtime from a secret manager.
- Rolling back means redeploying an earlier SHA.
