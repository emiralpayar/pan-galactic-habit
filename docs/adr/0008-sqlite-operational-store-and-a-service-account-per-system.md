# 0008. SQLite Operational Store and a service account per system

- **Status:** Accepted
- **Date:** 2026-09-19
- **Deciders:** @MGokcay

## Context

ARCHITECTURE.md §11 lists several open infrastructure questions that [issue #32](https://github.com/emiralpayar/pan-galactic-habit/issues/32) proposed to decide together. Only two are needed during Phase 1:

- **Operational Store technology (part of §11.1).** Per-time-window budget counters and write audit records live in the Operational Store (§5.2, §7) and are needed on the write path ([#13](https://github.com/emiralpayar/pan-galactic-habit/issues/13) item 4).
- **Write identity (§11.3).** The end-to-end write against a sandbox project ([#13](https://github.com/emiralpayar/pan-galactic-habit/issues/13) item 12) needs a decision on whose identity writes use. It is also listed as "to be defined in Phase 1" in `adapters/azure-devops/README.md`.

Hosting platform and secret manager (rest of §11.1), user authentication (§11.2), and shared LLM credentials (§11.7) are not needed until a shared deployment exists. By then we will know more about who the users are and whether on-behalf-of writes matter, so they stay open.

Constraints:

- The first users are a small, trusted team, and one shared service account is acceptable.
- Losing the Operational Store must not change what any habit does, and per-time-window budgets fail closed when the store is unavailable (§5.2, §7).
- The external system's own permissions are the outer boundary (§3, defense in depth).
- The Azure DevOps token may be stored on the team's own server; where exactly is decided with hosting.

## Decision

We will make two decisions now and leave the rest of §11.1, §11.2, and §11.7 open.

1. **Operational Store: SQLite behind a store port.** The Safety Layer and the rest of the code depend on a small store interface, not on SQLite directly, so Postgres or another engine can replace it without touching callers. If the store is unavailable, writes fail closed. Backups and where the file lives are decided with hosting.
2. **Write identity: one least-privilege service account per external system.**
   - Each service account has only the permissions its habits need, so the external system's own permissions stay a real outer boundary.
   - Attribution of a write to the confirming user comes from our audit records (which include the confirming user's ID), not from the external system's history. Adapters do not add user names to the external system's fields, because that would require allowlisting fields such as `System.History` in the Safety Policy.

## Consequences

**Easier:**

- The Phase 1 write path (budgets, audit records, the sandbox write) is unblocked without committing to a hosting platform.
- SQLite needs no extra service to run, and the store port keeps a later move to Postgres cheap.
- No per-user credential handling in adapters.

**Harder:**

- With one service account, every user who can confirm a write does so with the same permissions in the external system, and the external system no longer distinguishes them. The only per-user control left is our own authentication. When user authentication is implemented, that module is **safety-critical** and must be added to `scripts/checks/safety-critical-paths.txt` and `CODEOWNERS`.
- The external system's history shows the service account, not the person. Attribution depends on our audit records, which live in a non-authoritative store.
- SQLite limits the Operational Store to a single writer process. Scaling out needs the store swapped first.

**Open, to be decided with hosting and the web frontend:**

- Hosting platform and secret manager, including where company Azure DevOps credentials may be stored.
- User authentication, including where user accounts live. Accounts in the Operational Store would make losing it lose every account, which §7 does not currently say.
- LLM credentials for shared deployments and autonomous agents, including how they relate to [ADR 0004](0004-agent-runtime-port-with-claude-and-copilot-backends.md) (CI evals, the Copilot backend) and where any per-user token cap belongs.

## Alternatives considered

- **Decide hosting, authentication, and LLM credentials now (the original scope of this ADR).** Not chosen: they are not needed until a shared deployment exists, and the facts they depend on are not known yet.
- **Postgres from the start.** More capable, but a stateful service to run and back up for a non-authoritative, low-volume store. The store port keeps the switch cheap.
- **On-behalf-of writes under the confirming user's identity.** Best history in the external system, but requires SSO and per-user credential handling. Revisit with user authentication.
- **Add the confirming user's name to the change comment.** Rejected: it needs `System.History` in the Safety Policy allowlist, which is a `loosens` change, and puts user names in the external system.
