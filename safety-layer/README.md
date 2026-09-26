# Safety Layer

> **Status:** in progress — Phase 1. The Safety Policy loader and write validation exist; budgets, Write Confirmation, and audit do not. **Safety-critical.** Every change requires a `Safety-Impact` declaration and code owner approval.

The deterministic (non-LLM) engine that gates every write to an external system (ARCHITECTURE.md §2, §5.2). The engine is shared; what each habit may write is defined by that habit's `policy/`.

## Responsibilities

- Load and validate a habit's Safety Policy.
- Validate each proposed write **as a whole payload** (every payload operation and field), not by tool name. Non-mutating preconditions (e.g. a JSON Patch `test`) are allowed; operations that copy from another path (e.g. `move`, `copy`) are rejected.
- Enforce budgets per call, per session, and per time window.
- Produce the diff preview for Write Confirmation, and re-validate at execution time.
- Execute approved writes through the adapter. The engine is handed the adapter's write executor (an import contract stops it from importing an adapter), so it stays system-agnostic.
- Emit an audit record for every executed and rejected write.

## Invariants

These must hold for every change to this component, and must be covered by tests:

1. **No LLM calls.** Decisions are deterministic code.
2. **Deny by default.** Anything not explicitly allowed by the policy is rejected.
3. **Fail closed.** Errors, missing policy, unparseable payloads, or an unavailable budget store reject the write.
4. **No confirmation, no write.** A write without a matching user confirmation is rejected.
5. **No system-specific or habit-specific rules** in the engine — those belong in adapters and policies.

## Safety Policy format

Each habit's policy lives at `habits/<name>/policy/safety-policy.yaml` and is loaded with `safety_layer.policy.load_policy(path, habit=<name>)`.

```yaml
habit: backlog-refiner          # must match the habit loading it
writes:                         # empty or absent: a read-only habit
  - operation: update-work-item # an adapter operation name
    fields:                     # the only fields this operation may change
      - System.Description
budgets:                        # per_call <= per_session
  per_call: 1
  per_session: 10
  per_time_window:
    limit: 25
    window_minutes: 1440
```

- **Allowlist only.** There is no list of forbidden operations: anything not listed is denied, and a second list could only disagree with the first.
- **Opaque names.** Operation and field names are defined by the adapter (see its Operations table) and compared exactly; the engine never interprets them. They are printable ASCII without spaces.
- **Budget unit.** A budget counts write requests, each one call to an adapter write operation (for Azure DevOps, one work item update). `per_call` caps the writes in a single agent proposal.
- **Fail closed.** A missing or unreadable file, invalid YAML, unknown keys, wrong types, or a policy for another habit raise `PolicyError`. Duplicate keys, anchors, aliases, merge keys, explicit tags, and integers that are not plain decimal (`010`, `0x10`, `1:30`) are rejected too, because each can make the loaded policy differ from the diff a reviewer approved.
- **Only from the loader.** Code that enforces a policy must take it from `load_policy`, never build a `SafetyPolicy` directly: constructing one skips the file, the habit check, or (with `model_construct`) validation.
- **Write Confirmation is not configurable.** It is an engine invariant, so the policy has no setting for it.

## Write validation

`safety_layer.write_validation.validate(policy, request)` checks a `WriteRequest` (an operation name, an opaque adapter-defined target, and a tuple of `PayloadOperation`s) against the payload-level policy check in ARCHITECTURE.md §5.2. `target` is opaque and not inspected, and `WriteRequest` has no `parameters` field yet; a later change may extend the check to cover them.

- Every field of `request` is checked to be exactly the type `WriteRequest` promises (`type(...) is ...`, not `isinstance`), so a lookalike object with a permissive `__eq__` or a mutable `list` payload cannot pass as a well-formed request.
- The operation must be listed under `writes` in the policy.
- Every mutating payload operation (`add`, `replace`, `remove`) must target a field the policy allows for that operation.
- `test` is allowed as a precondition and never counts as a mutation.
- `move`, `copy`, any unknown `op`, and any operation carrying `from` are rejected outright, since none can be checked against a field allowlist.
- A request with no mutating operation is rejected: there is nothing for Write Confirmation to preview or confirm.
- The whole request is rejected if any single operation is rejected; nothing is ever partly applied.
- `validate` raises no `Exception`. An unexpected error is a rejection, like every other failure (fail closed).

Budgets, Write Confirmation, and audit are not implemented yet; passing `validate` is necessary but not sufficient to execute a write.

## Layout

| Path | Contents |
|---|---|
| `core/` | The generic engine: the `safety_layer` package and its tests |
