"""Every habit's committed Safety Policy must load, so a broken policy fails CI, not a session."""

from pathlib import Path

import pytest
from safety_layer.policy import load_policy

ROOT = Path(__file__).resolve().parents[1]
HABITS = sorted(path for path in (ROOT / "habits").iterdir() if path.is_dir())


def test_habits_are_found() -> None:
    assert HABITS, f"no habits under {ROOT / 'habits'}"


@pytest.mark.parametrize("habit", HABITS, ids=lambda path: path.name)
def test_habit_policy_loads(habit: Path) -> None:
    load_policy(habit / "policy" / "safety-policy.yaml", habit=habit.name)


def test_backlog_refiner_writes_only_its_three_fields() -> None:
    # ARCHITECTURE.md §6. Widening this is a `Safety-Impact: loosens` change.
    policy = load_policy(
        ROOT / "habits" / "backlog-refiner" / "policy" / "safety-policy.yaml",
        habit="backlog-refiner",
    )

    assert [(rule.operation, set(rule.fields)) for rule in policy.writes] == [
        (
            "update-work-item",
            {"System.Description", "Microsoft.VSTS.Common.AcceptanceCriteria", "System.Tags"},
        )
    ]
