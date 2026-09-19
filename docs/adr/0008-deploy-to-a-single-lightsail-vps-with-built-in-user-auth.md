# 0008. Deploy to a single Lightsail VPS with built-in user auth

- **Status:** Accepted
- **Date:** 2026-09-19
- **Deciders:** MGokcay

## Context

Phase 1 ends with a terminal chat interface run by one person. A hosted deployment for several people depends on four coupled open questions from ARCHITECTURE.md §11: hosting and the technology for the Operational Store and secret manager (§11.1), user authentication (§11.2), write identity in external systems (§11.3), and LLM credentials (§11.7). Full problem statement: [issue #32](https://github.com/emiralpayar/pan-galactic-habit/issues/32).

Constraints and facts:

- The first users are a small, trusted team.
- The first external system is Azure DevOps, but a single shared service account is acceptable for writes.
- A single instance, with the availability that implies, is acceptable to start.
- Personal subscription tokens are a stopgap; they will be replaced by API keys ([ADR 0004](0004-agent-runtime-port-with-claude-and-copilot-backends.md)).
- The deploy model is fixed: the image bakes in one commit and holds no authoritative state (§4.4, §7). Losing the Operational Store must not change what any habit does, and per-time-window budgets fail closed when the store is unavailable (§5.2).
- Simplicity matters more than scale right now, but the choices should not block a later move to managed services or SSO.

## Decision

We will deploy to **one AWS Lightsail instance** running Docker Compose, and decide the four questions together:

1. **Hosting and storage.**
   - One application image contains the Chat Interface, Safety Layer, adapters, and habits. A reverse proxy container (Caddy) terminates TLS and is not part of the application image.
   - CI publishes the image tagged with the commit SHA; a deploy pulls that tag.
   - The Operational Store is **SQLite on a mounted volume**, behind a small store interface so it can be swapped for Postgres later. The volume is backed up off-instance (Lightsail snapshots or a scheduled copy).
   - Secrets are supplied at runtime, never baked into the image: a root-only env file on the instance, or AWS SSM Parameter Store read through the instance role.
2. **User authentication.** The Chat Interface has built-in authentication: a user table with argon2-hashed passwords and server-side sessions stored in the Operational Store. An admin creates users with a CLI command; there is no self-signup. Login attempts are rate limited. The auth layer sits behind an interface so an external identity provider (for example Entra ID) can replace it later.
3. **Write identity.** Writes to external systems use **one shared service account per system**. Every audit record includes the ID of the user who confirmed the write, and adapters include that user's name in the change comment where the external system allows it, so attribution survives the shared identity.
4. **LLM credentials.** Shared deployments and autonomous agents use **API keys**, with a separate key for each of: the deployed chat, CI evals, and the Improver and Orchestrator. Each key has a provider-side spend limit. The Safety Policy adds a per-user token cap so one user cannot exhaust the shared budget. Personal subscription tokens remain valid for single-user local runs only.

## Consequences

**Easier:**

- One instance, one Compose file, one image: cheap, quick to stand up, and easy to reason about.
- No managed database or identity provider to provision, and no Azure dependency beyond Azure DevOps itself.
- Separate, capped API keys make LLM spend attributable and individually revocable.
- Per-user audit attribution is available without on-behalf-of credentials.

**Harder:**

- A single instance is a single point of failure: no redundancy, and deploys cause brief downtime.
- SQLite limits the deployment to one instance; scaling out requires the Postgres swap first.
- Built-in auth means we own password handling, session security, and user administration. That is acceptable for a trusted team but does not scale to an open user base.
- With a shared service account, the external system's own history shows the service account, not the person. Attribution depends on our audit records and comments.
- Secrets in an env file are weaker than a managed secret manager; SSM reduces this but adds an AWS dependency.

**Follow-ups:**

- Follow-up issues for the web frontend (on the same session core as the terminal interface) and the deploy workflow in `deploy/`.
- This decision should be revisited if the user base grows beyond a trusted team, if availability requirements rise, or if on-behalf-of writes become a requirement (which SSO would enable).

## Alternatives considered

- **Azure Container Apps + Entra ID + Key Vault + Postgres.** The candidate named in the issue. It gives SSO, on-behalf-of Azure DevOps writes, managed secrets, and redundancy. Not chosen because the added services and cost are not needed for a small trusted team on one instance; it stays the likely next step if needs grow.
- **Postgres in Compose from the start.** More capable than SQLite, but an extra stateful container to run and back up. The Operational Store is non-authoritative and low volume, so SQLite is enough; the store interface keeps the switch cheap.
- **Entra ID or another SSO provider now.** Better for access management and enables on-behalf-of writes, but adds setup and an external dependency that a trusted team doesn't need yet. The auth interface keeps the door open.
- **On-behalf-of writes under the confirming user's identity.** Best audit history in the external system, but requires SSO and per-user credential handling. Deferred; audit records and comments cover attribution for now.
- **Shared personal subscription tokens.** Not viable for several users and to be replaced by API keys anyway.
