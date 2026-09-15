# Lobes

A lobe is an independent agentic flow with one purpose, its own memory, its own Safety Policy, and its own evals (ARCHITECTURE.md §2, §5).

## Structure

Every lobe follows this layout:

```text
lobes/<name>/
  README.md               # purpose, external system, reads, writes, status
  agent/                  # agent definition and flow code
  memory/
    instructions.md       # see docs/development/memory-style-guide.md
    skills/*.md
  policy/
    safety-policy.yaml    # field allowlist, forbidden operations, budgets  [safety-critical]
  evals/
    fixtures/             # synthetic inputs
    cases/                # expected qualities per fixture
```

## Rules for changes

- The directory name is lowercase kebab-case and is automatically a valid commit scope.
- **Memory is read-only at runtime.** Changes to memory are PRs, committed as `feat(<lobe>)` or `fix(<lobe>)`.
- **`policy/` is safety-critical.** Any change needs `Safety-Impact` and code owner approval. The policy is deny-by-default.
- **Memory cannot grant permissions** — only the policy defines what a lobe may write.
- Behavior and memory changes add or update eval cases.
- Eval fixtures are synthetic or fully anonymized.
- Agent code never calls adapter write functions directly; writes go through the Safety Layer.

## Lobes

| Lobe | Purpose | External system | Status |
|---|---|---|---|
| [backlog-refiner](backlog-refiner/) | Refine backlog items against a Definition of Ready | Azure DevOps | Not started (Phase 1) |
