import threading
from pathlib import Path

import pytest

from safety_layer.budgets import BudgetRejection, Reservation, SessionBudget
from safety_layer.policy import PolicyError, SafetyPolicy, load_policy

POLICY = """\
habit: example-habit
writes:
  - operation: update-record
    fields: [title]
budgets:
  per_call: 2
  per_session: 3
  per_time_window:
    limit: 20
    window_minutes: 1440
"""


@pytest.fixture
def policy(tmp_path: Path) -> SafetyPolicy:
    path = tmp_path / "safety-policy.yaml"
    path.write_text(POLICY, encoding="utf-8")
    return load_policy(path, habit="example-habit")


@pytest.fixture
def budget(policy: SafetyPolicy) -> SessionBudget:
    return SessionBudget(policy)


def _reserved(result: Reservation | BudgetRejection) -> Reservation:
    assert isinstance(result, Reservation), result
    return result


def test_a_proposal_within_both_budgets_is_reserved(budget: SessionBudget) -> None:
    reservation = _reserved(budget.reserve(2))

    assert reservation.count == 2
    assert budget.remaining == 1


def test_a_proposal_over_per_call_is_rejected_whole_and_reserves_nothing(
    budget: SessionBudget,
) -> None:
    result = budget.reserve(3)

    assert isinstance(result, BudgetRejection)
    assert "per-call budget of 2" in result.reason
    assert budget.remaining == 3


def test_writes_stop_at_exactly_per_session(budget: SessionBudget) -> None:
    _reserved(budget.reserve(2)).commit()
    _reserved(budget.reserve(1)).commit()

    result = budget.reserve(1)
    assert isinstance(result, BudgetRejection)
    assert "per-session budget of 3" in result.reason
    assert budget.remaining == 0


def test_pending_reservations_count_against_the_session(budget: SessionBudget) -> None:
    first = _reserved(budget.reserve(2))

    assert isinstance(budget.reserve(2), BudgetRejection)
    second = _reserved(budget.reserve(1))
    assert isinstance(budget.reserve(1), BudgetRejection)
    assert (first.count, second.count, budget.remaining) == (2, 1, 0)


def test_a_released_reservation_returns_its_budget(budget: SessionBudget) -> None:
    _reserved(budget.reserve(2)).release()

    assert budget.remaining == 3
    _reserved(budget.reserve(2))


def test_a_committed_reservation_does_not_return_its_budget(budget: SessionBudget) -> None:
    _reserved(budget.reserve(2)).commit()

    assert budget.remaining == 1
    assert isinstance(budget.reserve(2), BudgetRejection)


@pytest.mark.parametrize(
    ("first", "second"),
    [("commit", "commit"), ("commit", "release"), ("release", "commit"), ("release", "release")],
)
def test_a_reservation_settles_only_once(budget: SessionBudget, first: str, second: str) -> None:
    # Committing after a release would execute a write whose budget was given back.
    reservation = _reserved(budget.reserve(1))
    getattr(reservation, first)()
    remaining = budget.remaining

    with pytest.raises(RuntimeError, match="already settled"):
        getattr(reservation, second)()
    assert budget.remaining == remaining


@pytest.mark.parametrize("settle", ["commit", "release"])
def test_a_reservation_not_issued_by_the_budget_cannot_settle(
    budget: SessionBudget, settle: str
) -> None:
    _reserved(budget.reserve(2))
    forged = Reservation(2, budget)

    with pytest.raises(RuntimeError, match="never issued"):
        getattr(forged, settle)()
    assert budget.remaining == 1


def test_a_reservation_count_cannot_be_changed(budget: SessionBudget) -> None:
    reservation = _reserved(budget.reserve(1))

    with pytest.raises(AttributeError):
        reservation.count = 100  # type: ignore[misc]
    object.__setattr__(reservation, "count", 100)
    reservation.release()
    assert budget.remaining == 3


def test_a_reservation_settles_only_with_its_own_budget(policy: SafetyPolicy) -> None:
    one, other = SessionBudget(policy), SessionBudget(policy)
    _reserved(one.reserve(1)).commit()

    assert (one.remaining, other.remaining) == (2, 3)


@pytest.mark.parametrize(
    "count",
    [
        pytest.param(0, id="zero"),
        pytest.param(-1, id="negative"),
        pytest.param(True, id="bool"),
        pytest.param(1.0, id="float"),
        pytest.param("1", id="string"),
        pytest.param(None, id="none"),
        pytest.param(type("Count", (int,), {})(1), id="int-subclass"),
    ],
)
def test_a_bad_count_is_rejected_not_raised(budget: SessionBudget, count: object) -> None:
    result = budget.reserve(count)  # type: ignore[arg-type]

    assert isinstance(result, BudgetRejection)
    assert budget.remaining == 3


def test_an_unexpected_error_is_a_rejection(
    budget: SessionBudget, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken(_: int) -> None:
        raise ZeroDivisionError

    monkeypatch.setattr(budget, "_check", broken)
    result = budget.reserve(1)

    assert isinstance(result, BudgetRejection)
    assert result.reason == "the budget check failed"
    assert budget.remaining == 3


@pytest.mark.parametrize(
    "budgets",
    [
        pytest.param({"per_call": 0, "per_session": 3}, id="zero-per-call"),
        pytest.param({"per_call": 4, "per_session": 3}, id="call-over-session"),
        pytest.param({"per_call": 1, "per_session": None}, id="missing-per-session"),
    ],
)
def test_a_policy_with_invalid_budgets_builds_no_tracker(
    policy: SafetyPolicy, budgets: dict[str, object]
) -> None:
    # `model_construct` skips validation, which a policy from `load_policy` never does.
    broken = policy.budgets.model_construct(**{**dict(policy.budgets), **budgets})
    unchecked = policy.model_construct(**{**dict(policy), "budgets": broken})

    with pytest.raises(PolicyError, match="budgets"):
        SessionBudget(unchecked)


def test_concurrent_reservations_never_exceed_the_session(policy: SafetyPolicy) -> None:
    budget = SessionBudget(policy)
    results: list[Reservation | BudgetRejection] = []
    start = threading.Barrier(20)

    def reserve() -> None:
        start.wait()
        results.append(budget.reserve(1))

    threads = [threading.Thread(target=reserve) for _ in range(20)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sum(isinstance(result, Reservation) for result in results) == 3
    assert budget.remaining == 0
