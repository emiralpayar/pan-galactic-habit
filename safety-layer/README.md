# Safety Layer

> **Status:** not started — Phase 1. **Safety-critical.** Every change requires a `Safety-Impact` declaration and code owner approval.

The deterministic (non-LLM) engine that gates every write to an external system (ARCHITECTURE.md §2, §5.2). The engine is shared; what each habit may write is defined by that habit's `policy/`.

## Responsibilities

- Load and validate a habit's Safety Policy.
- Validate each proposed write **as the complete request** the adapter built (target, parameters, and every payload operation and field), not by tool name. Non-mutating preconditions (e.g. a JSON Patch `test`) are allowed; operations that copy from another path (e.g. `move`, `copy`) are rejected.
- Enforce budgets per call, per session, and per time window.
- Produce the diff preview for Write Confirmation, and re-validate at execution time.
- Execute approved writes through the adapter.
- Emit an audit record for every executed and rejected write.

## Invariants

These must hold for every change to this component, and must be covered by tests:

1. **No LLM calls.** Decisions are deterministic code.
2. **Deny by default.** Anything not explicitly allowed by the policy is rejected.
3. **Fail closed.** Errors, missing policy, unparseable payloads, or an unavailable budget store reject the write.
4. **No confirmation, no write.** A write without a matching user confirmation is rejected.
5. **No system-specific or habit-specific rules** in the engine — those belong in adapters and policies.

## Layout

| Path | Contents |
|---|---|
| `core/` | The generic engine |
