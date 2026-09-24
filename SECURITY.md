# Security Policy

pan-galactic-habit runs agents that can write to external systems. A vulnerability here can mean unintended changes to real data, so we treat security reports as a priority.

## Reporting a vulnerability

**Do not open a public issue or pull request.**

Report privately to the maintainers listed in `.github/CODEOWNERS`, by direct message, with:

- what the issue is and which component it affects,
- steps to reproduce (with synthetic data),
- the impact you believe it has — especially whether it can cause a write that the Safety Layer should have blocked.

You can expect an acknowledgement within two business days.

## What counts as a vulnerability

In addition to the usual classes (secret exposure, injection, privilege escalation), the following are security issues in this project:

- Any way for a habit to **write to an external system without passing through the Safety Layer**, or to write something its Safety Policy does not allow.
- Any way for **content read from an external system** (prompt injection) to cause writes beyond what the user confirmed.
- Any way for an agent to **approve or merge a pull request into `main`**, or to change `main` without review.
- Any way for a development loop session to **approve or merge into `main`**, to **merge into `agent-main` without the other agent account's approval**, for an agent account to become a code owner, or to get past the guard hook's `agent-main` base check or the `protect-agent-main` ruleset ([ADR 0010](docs/adr/0010-development-agents-integrate-on-an-agent-main-branch.md)).
- A Safety Layer path that **fails open**.
- Exposure of **credentials** used by adapters, agents, or CI.

## Handling secrets

- Secrets never go into the repository, container images, logs, or eval fixtures.
- Local development uses `.env` (gitignored); deployed environments use a secret manager.
- Credentials are least-privilege and scoped per purpose (see ARCHITECTURE.md §8).
- **If a secret is committed, it is compromised.** Rotate it first, then clean history, then tell the maintainers.

## Recommended repository settings

Repository admins should enable, where the plan allows:

- Secret scanning and push protection.
- Dependabot alerts and security updates.
- The `protect-main` ruleset (`scripts/bootstrap-github.sh`).
