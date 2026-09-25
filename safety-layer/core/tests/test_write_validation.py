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

    result = validate(POLICY, request)

    assert isinstance(result, Rejected)
    assert "unexpected error" in result.reason


def test_an_unexpected_error_is_rejected_instead_of_raising() -> None:
    request = WriteRequest(operation="update-record", target="1", payload=123)  # type: ignore[arg-type]

    result = validate(POLICY, request)

    assert isinstance(result, Rejected)
    assert "unexpected error" in result.reason
