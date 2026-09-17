# Architecture Decision Records

An ADR captures one significant decision: the context, what was decided, and the consequences. [ARCHITECTURE.md](../../ARCHITECTURE.md) describes the system *as it is*; ADRs explain *why* it is that way.

## When to write one

Write an ADR when a decision:

- is hard or expensive to reverse,
- affects more than one component,
- resolves an open question in ARCHITECTURE.md §11, or
- chooses between reasonable alternatives that a future contributor might revisit.

Easily reversible choices local to one component don't need an ADR; a good PR description is enough.

## How

1. `make adr title="short decision title"` (or `scripts/new-adr.sh "…"`, or the `new-adr` Claude Code skill).
2. Fill in every section. Status is `Accepted` if this PR already carries out the decision — the common case, since a PR is normally opened once the decision is made. Use `Proposed` only if you're opening the PR to put the decision up for discussion before it's made.
3. Add it to the index below, with the same status, and update ARCHITECTURE.md if the decision changes it.
4. Open a PR. If the ADR was `Proposed`, flip it (and its index entry) to `Accepted` once the decision is actually made — before merging, or in a follow-up PR if the decision firms up after merge.

## Rules

- ADRs are **immutable once accepted**. To change a decision, write a new ADR and mark the old one `Superseded by NNNN`.
- Statuses: `Proposed`, `Accepted`, `Rejected`, `Deprecated`, `Superseded by NNNN`.
- Numbers are never reused.

## Index

| # | Title | Status |
|---|---|---|
| [0001](0001-record-architecture-decisions.md) | Record architecture decisions | Accepted |
| [0002](0002-trunk-based-development-with-protected-main.md) | Trunk-based development with a protected main | Accepted |
| [0003](0003-use-python-as-the-implementation-language.md) | Use Python as the implementation language | Accepted |
| [0004](0004-agent-runtime-port-with-claude-and-copilot-backends.md) | Agent runtime port with Claude and Copilot backends | Accepted |
| [0005](0005-azure-devops-adapter-calls-the-rest-api-directly.md) | Azure DevOps adapter calls the REST API directly | Accepted |
| [0006](0006-rename-lobe-to-habit.md) | Rename "lobe" to "habit" | Proposed |
