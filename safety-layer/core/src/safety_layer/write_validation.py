"""Validates a proposed write against a habit's Safety Policy.

The engine checks the complete write request an adapter built (its target and every
payload operation and field), never just an operation name, as safety-layer/README.md
and ARCHITECTURE.md §5.2 require. `validate` only decides whether a request may proceed;
it never applies anything, and passing it is not enough to execute a write, since budgets
and Write Confirmation still gate execution.
"""

from __future__ import annotations

from dataclasses import dataclass

from safety_layer.policy import SafetyPolicy

__all__ = [
    "Accepted",
    "PayloadOperation",
    "Rejected",
    "ValidationResult",
    "WriteRequest",
    "validate",
]

# JSON Patch operations that change a field's value; each must target a field the policy
# allows for the request's operation.
_MUTATING_OPS = frozenset({"add", "replace", "remove"})
# The only non-mutating operation the engine allows, as a precondition (e.g. a revision
# check). It never counts as a mutation and is never checked against the field allowlist.
_PRECONDITION_OP = "test"


@dataclass(frozen=True, slots=True)
class PayloadOperation:
    """One JSON Patch-shaped operation in a write request's payload.

    `op` and `field` are adapter-defined opaque identifiers (safety-layer/README.md):
    compared exactly, never interpreted. `from_field` is set only by an operation that
    copies from another path (`move`, `copy`); the engine rejects that shape outright, so
    its value is never inspected.
    """

    op: str
    field: str
    from_field: str | None = None


@dataclass(frozen=True, slots=True)
class WriteRequest:
    """The complete write an adapter is about to send, before the Safety Layer checks it.

    `target` is opaque to the engine (an adapter-defined identifier, e.g. a work item id);
    only the adapter and the audit record interpret it.
    """

    operation: str
    target: str
    payload: tuple[PayloadOperation, ...]


@dataclass(frozen=True, slots=True)
class Accepted:
    """The request passed every check here."""


@dataclass(frozen=True, slots=True)
class Rejected:
    """The request was refused, and `reason` says why. Never partially applied."""

    reason: str


type ValidationResult = Accepted | Rejected


def validate(policy: SafetyPolicy, request: WriteRequest) -> ValidationResult:
    """Check `request` against `policy`. Deny by default; fail closed on any error.

    Every mutating operation (`add`, `replace`, `remove`) must target a field the policy
    allows for `request.operation`. `test` is allowed and never counts as a mutation.
    `move`, `copy`, an unknown `op`, and any operation carrying `from_field` are rejected
    outright, since none of them can be checked against a field allowlist. A request with
    no mutating operation is rejected too: there is nothing for Write Confirmation to
    preview or confirm.

    Never raises: this runs on every write, so an unexpected error (a malformed request,
    a bug here) must reject rather than crash or, worse, let the write through
    (invariant 3, fail closed).
    """
    try:
        return _validate(policy, request)
    except Exception as error:  # deliberately broad: any failure here must reject, not raise
        return Rejected(f"unexpected error validating the write: {error}")


def _validate(policy: SafetyPolicy, request: WriteRequest) -> ValidationResult:
    if not any(rule.operation == request.operation for rule in policy.writes):
        return Rejected(f"operation {request.operation!r} is not allowed")

    if not request.payload:
        return Rejected("a write request must have at least one payload operation")

    mutates = False
    for operation in request.payload:
        if operation.from_field is not None:
            return Rejected(f"operation {operation.op!r} may not carry 'from'")
        if operation.op == _PRECONDITION_OP:
            continue
        if operation.op not in _MUTATING_OPS:
            return Rejected(f"operation {operation.op!r} is not allowed")
        if not policy.allows(request.operation, operation.field):
            return Rejected(
                f"{request.operation!r} may not {operation.op} field {operation.field!r}"
            )
        mutates = True

    if not mutates:
        return Rejected("a write request must contain at least one mutating operation")

    return Accepted()
