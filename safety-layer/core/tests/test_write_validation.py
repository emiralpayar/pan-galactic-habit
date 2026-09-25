import pytest

from safety_layer.policy import Budgets, SafetyPolicy, TimeWindowBudget, WriteRule
from safety_layer.write_validation import (
    Accepted,
    PayloadOperation,
    Rejected,
    WriteRequest,
    validate,
)

POLICY = SafetyPolicy(
    habit="example-habit",
    writes=(
        WriteRule(operation="update-record", fields=("title", "body")),
        WriteRule(operation="close-record", fields=("state",)),
    ),
    budgets=Budgets(
        per_call=1, per_session=5, per_time_window=TimeWindowBudget(limit=20, window_minutes=1440)
    ),
)


def _request(*payload: PayloadOperation, operation: str = "update-record") -> WriteRequest:
    return WriteRequest(operation=operation, target="1", payload=payload)


def test_a_request_with_one_allowed_mutation_is_accepted() -> None:
    request = _request(PayloadOperation(op="replace", field="title"))

    assert validate(POLICY, request) == Accepted()


def test_a_request_with_a_precondition_and_an_allowed_mutation_is_accepted() -> None:
    request = _request(
        PayloadOperation(op="test", field="title"),
        PayloadOperation(op="replace", field="body"),
    )

    assert validate(POLICY, request) == Accepted()


def test_an_operation_not_in_the_policy_is_rejected() -> None:
    request = _request(PayloadOperation(op="replace", field="title"), operation="delete-record")

    assert validate(POLICY, request) == Rejected("operation 'delete-record' is not allowed")


def test_a_mutation_on_a_field_not_allowed_for_the_operation_is_rejected() -> None:
    request = _request(PayloadOperation(op="replace", field="state"))

    result = validate(POLICY, request)

    assert result == Rejected("'update-record' may not replace field 'state'")


def test_the_whole_request_is_rejected_even_when_other_operations_are_allowed() -> None:
    request = _request(
        PayloadOperation(op="replace", field="title"),
        PayloadOperation(op="replace", field="state"),
    )

    assert isinstance(validate(POLICY, request), Rejected)


def test_a_precondition_alone_is_rejected_as_no_mutation() -> None:
    request = _request(PayloadOperation(op="test", field="title"))

    assert validate(POLICY, request) == Rejected(
        "a write request must contain at least one mutating operation"
    )


def test_an_empty_payload_is_rejected() -> None:
    request = _request()

    assert validate(POLICY, request) == Rejected(
        "a write request must have at least one payload operation"
    )


@pytest.mark.parametrize("op", ["move", "copy", "remove"])
def test_an_operation_carrying_from_is_rejected(op: str) -> None:
    request = _request(PayloadOperation(op=op, field="title", from_field="body"))

    result = validate(POLICY, request)

    assert result == Rejected(f"operation {op!r} may not carry 'from'")


@pytest.mark.parametrize("op", ["move", "copy", "unlink", ""])
def test_an_unknown_or_copying_op_without_from_is_rejected(op: str) -> None:
    request = _request(PayloadOperation(op=op, field="title"))

    assert validate(POLICY, request) == Rejected(f"operation {op!r} is not allowed")


def test_field_and_operation_names_are_compared_exactly() -> None:
    request = _request(PayloadOperation(op="replace", field="Title"))

    assert isinstance(validate(POLICY, request), Rejected)


def test_malformed_input_is_rejected_instead_of_raising() -> None:
    class _NotAPayloadOperation:
        from_field = None

    request = WriteRequest(
        operation="update-record",
        target="1",
        payload=(_NotAPayloadOperation(),),  # type: ignore[arg-type]
    )

    assert validate(POLICY, request) == Rejected("malformed write request")


def test_a_non_tuple_payload_is_rejected_as_malformed() -> None:
    request = WriteRequest(operation="update-record", target="1", payload=123)  # type: ignore[arg-type]

    assert validate(POLICY, request) == Rejected("malformed write request")


def test_a_list_payload_is_rejected_as_malformed() -> None:
    # A list can be mutated after validation and before the write is sent; only a tuple
    # is accepted.
    request = WriteRequest(
        operation="update-record",
        target="1",
        payload=[PayloadOperation(op="replace", field="title")],  # type: ignore[arg-type]
    )

    assert validate(POLICY, request) == Rejected("malformed write request")


def test_a_generator_payload_is_rejected_as_malformed() -> None:
    # A generator is consumed by inspecting it, so what would be checked is not what
    # would be sent.
    payload = (op for op in (PayloadOperation(op="replace", field="title"),))
    request = WriteRequest(operation="update-record", target="1", payload=payload)  # type: ignore[arg-type]

    assert validate(POLICY, request) == Rejected("malformed write request")


class _EqAnything(str):
    """A `str` subclass that compares equal to everything. `type(...) is str` rejects
    it; `==` and `in`, which the pre-fix code relied on, would not."""

    def __eq__(self, other: object) -> bool:
        return True

    def __hash__(self) -> int:
        return hash(str(self))


def test_a_str_subclass_with_a_permissive_eq_cannot_bypass_the_field_allowlist() -> None:
    request = _request(PayloadOperation(op="replace", field=_EqAnything("state")))

    assert validate(POLICY, request) == Rejected("malformed write request")


def test_a_str_subclass_with_a_permissive_eq_cannot_bypass_the_precondition_check() -> None:
    # Without the type check, this op would compare equal to "test" (skipping the field
    # allowlist) while still not being the string "test" itself.
    request = _request(
        PayloadOperation(op=_EqAnything("move"), field="state"),
        PayloadOperation(op="replace", field="title"),
    )

    assert validate(POLICY, request) == Rejected("malformed write request")


def test_an_operation_object_with_a_permissive_eq_cannot_bypass_the_operation_allowlist() -> None:
    request = _request(
        PayloadOperation(op="replace", field="title"), operation=_EqAnything("delete-record")
    )

    assert validate(POLICY, request) == Rejected("malformed write request")


@pytest.mark.parametrize("op", ["add", "replace", "remove"])
def test_each_mutating_op_on_an_allowed_field_is_accepted(op: str) -> None:
    request = _request(PayloadOperation(op=op, field="title"))

    assert validate(POLICY, request) == Accepted()


def test_a_policy_whose_allows_raises_is_rejected_instead_of_raising() -> None:
    class _RaisingPolicy:
        writes = POLICY.writes

        def allows(self, operation: str, field: str) -> bool:
            raise RuntimeError("boom")

    request = _request(PayloadOperation(op="replace", field="title"))

    result = validate(_RaisingPolicy(), request)  # type: ignore[arg-type]

    assert result == Rejected("unexpected error validating the write: RuntimeError")
