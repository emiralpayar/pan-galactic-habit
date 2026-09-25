"""Per-call and per-session write budgets (ARCHITECTURE.md §5.2).

A budget counts write requests, each one call to an adapter write operation. A proposal
reserves its writes up front; each reservation is later committed when its writes execute,
or released when they are rejected or not confirmed. Pending reservations count against
the session, so two proposals waiting for confirmation cannot together exceed it.

Per-session counters live in process memory, which §5.2 allows. Per-time-window budgets
need the Operational Store and are not enforced here.
"""

import threading
from dataclasses import dataclass, field

from safety_layer.policy import Budgets, PolicyError, SafetyPolicy

__all__ = ["BudgetRejection", "Reservation", "SessionBudget"]


@dataclass(frozen=True, slots=True)
class BudgetRejection:
    """The proposal was not reserved. Nothing in it may be written."""

    reason: str


# `eq=False` keeps identity equality and hashing, so the budget can hold its open reservations.
@dataclass(eq=False, slots=True)
class Reservation:
    """Budget held for one proposal's writes, until it is committed or released once."""

    count: int
    _budget: "SessionBudget" = field(repr=False)

    def commit(self) -> None:
        """The writes executed: the budget stays spent."""
        self._budget._settle(self, spent=True)

    def release(self) -> None:
        """The writes were rejected or not confirmed: the budget is returned."""
        self._budget._settle(self, spent=False)


class SessionBudget:
    """The write budget of one session. Thread-safe.

    Build it from a policy returned by `load_policy`, one per session; a new instance
    starts a new session budget.
    """

    def __init__(self, policy: SafetyPolicy) -> None:
        # A policy from `load_policy` is already valid. Validating again means a policy
        # built with `model_construct` cannot bring a missing or impossible budget here.
        try:
            self._budgets = Budgets.model_validate(policy.budgets.model_dump())
        except Exception as error:
            raise PolicyError(f"invalid budgets: {error}") from error
        self._lock = threading.Lock()
        self._committed = 0
        self._pending = 0
        # Only reservations this budget issued may settle against it: releasing one built
        # by hand would lower the pending count and hand out budget nobody reserved.
        self._open: set[Reservation] = set()

    @property
    def remaining(self) -> int:
        """Writes the session can still reserve."""
        with self._lock:
            return self._budgets.per_session - self._committed - self._pending

    def reserve(self, count: int) -> Reservation | BudgetRejection:
        """Reserve `count` writes for one proposal, or reject the whole proposal.

        Never raises: a bad count or an unexpected error is a rejection, and nothing is
        reserved.
        """
        try:
            with self._lock:
                if rejection := self._check(count):
                    return rejection
                self._pending += count
                reservation = Reservation(count, self)
                self._open.add(reservation)
                return reservation
        except Exception:
            return BudgetRejection("the budget check failed")

    def _check(self, count: int) -> BudgetRejection | None:
        if isinstance(count, bool) or not isinstance(count, int) or count <= 0:
            return BudgetRejection("a proposal must contain a positive whole number of writes")
        per_call = self._budgets.per_call
        if count > per_call:
            return BudgetRejection(f"{count} writes exceeds the per-call budget of {per_call}")
        per_session = self._budgets.per_session
        if self._committed + self._pending + count > per_session:
            return BudgetRejection(
                f"{count} writes exceeds the per-session budget of {per_session}"
            )
        return None

    def _settle(self, reservation: Reservation, *, spent: bool) -> None:
        with self._lock:
            # Settling twice would count a write twice, or execute one whose budget was
            # already returned, so it is a bug to stop, not a case to handle.
            if reservation not in self._open:
                raise RuntimeError(
                    "the reservation is not open: it was already settled or never issued here"
                )
            self._open.remove(reservation)
            self._pending -= reservation.count
            if spent:
                self._committed += reservation.count
