"""The Safety Policy: what one habit may write, loaded deny-by-default and fail-closed.

A policy is an allowlist. It names the adapter operations a habit may call and, for each
one, the fields that operation may change. Anything not listed is not allowed, so there is
no separate list of forbidden operations to keep consistent with it.

Operation and field names are opaque identifiers defined by the adapter (for Azure DevOps,
field reference names such as ``System.Description``). The engine compares them exactly
and never interprets them, which keeps it free of system-specific rules (invariant 5).
"""

from pathlib import Path
from typing import Annotated, Any, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, Strict, ValidationError, model_validator

__all__ = [
    "Budgets",
    "PolicyError",
    "SafetyPolicy",
    "TimeWindowBudget",
    "WriteRule",
    "load_policy",
]


class PolicyError(Exception):
    """The policy could not be loaded. The only outcome is to allow nothing."""


# Strict types stop YAML's implicit typing from changing a value's meaning, e.g. `no`
# loading as a boolean or `3.0` passing as an integer budget.
PositiveInt = Annotated[int, Strict(), Field(gt=0)]
# Printable ASCII only, so a name cannot differ from what a reviewer sees by an invisible
# or look-alike character.
Identifier = Annotated[str, Strict(), Field(pattern=r"^[\x21-\x7e]+$")]
HabitName = Annotated[str, Strict(), Field(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


def _duplicates(values: tuple[str, ...]) -> set[str]:
    return {value for value in values if values.count(value) > 1}


class WriteRule(_Model):
    """One adapter operation the habit may call, and the only fields it may change."""

    operation: Identifier
    fields: tuple[Identifier, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _fields_are_unique(self) -> Self:
        if duplicates := _duplicates(self.fields):
            raise ValueError(f"duplicate fields: {sorted(duplicates)}")
        return self


class TimeWindowBudget(_Model):
    limit: PositiveInt
    window_minutes: PositiveInt


class Budgets(_Model):
    """Write caps. They are enforced by the engine, not here (ARCHITECTURE.md §5.2)."""

    per_call: PositiveInt
    per_session: PositiveInt
    per_time_window: TimeWindowBudget

    @model_validator(mode="after")
    def _call_fits_in_session(self) -> Self:
        # A session is made of calls, so a smaller session cap is almost certainly a typo. The
        # time window is not compared: a short window may reasonably cap below a session.
        if self.per_call > self.per_session:
            raise ValueError("budgets must satisfy per_call <= per_session")
        return self


class SafetyPolicy(_Model):
    habit: HabitName
    # Empty means a read-only habit: its Tool Surface gets no write tools at all.
    writes: tuple[WriteRule, ...] = ()
    budgets: Budgets

    @model_validator(mode="after")
    def _operations_are_unique(self) -> Self:
        # Two rules for one operation would make the allowed fields depend on which is read.
        if duplicates := _duplicates(tuple(rule.operation for rule in self.writes)):
            raise ValueError(f"duplicate operations: {sorted(duplicates)}")
        return self

    def allows(self, operation: str, field: str) -> bool:
        """Whether ``operation`` may change ``field``. Anything unlisted is denied."""
        return any(rule.operation == operation and field in rule.fields for rule in self.writes)


# In a policy, each of these could make the diff a reviewer approves differ from what is
# loaded, so all of them are rejected: duplicate keys (PyYAML keeps the last), anchors,
# aliases, and merge keys (a value depends on text elsewhere), explicit tags (`!!int '0x10'`),
# and YAML 1.1 integer spellings (`010` is 8, `1:30` is 90).


def _is_plain_decimal(text: str) -> bool:
    digits = text.removeprefix("-")
    return digits.isascii() and digits.isdigit() and (digits == "0" or digits[0] != "0")


class _StrictLoader(yaml.SafeLoader):
    """A safe loader that rejects ambiguous mapping keys and non-decimal integers."""

    def construct_yaml_int(self, node: Any) -> int:
        text = self.construct_scalar(node)
        if not isinstance(text, str) or not _is_plain_decimal(text):
            raise yaml.constructor.ConstructorError(
                None, None, f"integer {text!r} is not plain decimal", node.start_mark
            )
        return int(text)

    def construct_mapping(self, node: Any, deep: bool = False) -> dict[Any, Any]:
        seen: set[str] = set()
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, str) or key == "<<":
                raise yaml.constructor.ConstructorError(
                    None, None, f"key {key!r} is not allowed", key_node.start_mark
                )
            if key in seen:
                raise yaml.constructor.ConstructorError(
                    None, None, f"duplicate key {key!r}", key_node.start_mark
                )
            seen.add(key)
        return super().construct_mapping(node, deep=deep)


_StrictLoader.add_constructor("tag:yaml.org,2002:int", _StrictLoader.construct_yaml_int)


def _parse_yaml(text: str) -> Any:
    # Anchors, aliases, and tags are resolved before construction, so they are caught as events.
    for event in yaml.parse(text, Loader=yaml.SafeLoader):
        if isinstance(event, yaml.AliasEvent) or (
            isinstance(event, yaml.NodeEvent) and event.anchor is not None
        ):
            raise yaml.YAMLError(f"anchors and aliases are not allowed{event.start_mark}")
        if isinstance(event, (yaml.ScalarEvent, yaml.CollectionStartEvent)) and event.tag:
            raise yaml.YAMLError(f"explicit tags are not allowed{event.start_mark}")
    loader = _StrictLoader(text)
    try:
        return loader.get_single_data()
    finally:
        loader.dispose()


def load_policy(path: Path, *, habit: str) -> SafetyPolicy:
    """Load and validate the Safety Policy at ``path`` for ``habit``.

    Raises ``PolicyError`` on any failure. There is deliberately no fallback: a policy
    that cannot be loaded must result in no writes, never in a default.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise PolicyError(f"cannot read policy {path}: {error}") from error

    try:
        data = _parse_yaml(text)
    # Deliberately broad: PyYAML also raises ValueError (e.g. an impossible date) and
    # RecursionError (deep nesting), and every failure must surface as PolicyError.
    except Exception as error:
        raise PolicyError(f"invalid YAML in policy {path}: {error}") from error

    if not isinstance(data, dict):
        raise PolicyError(f"policy {path} must be a mapping, not {type(data).__name__}")

    try:
        policy = SafetyPolicy.model_validate(data)
    except ValidationError as error:
        raise PolicyError(f"invalid policy {path}: {error}") from error

    # Guards against wiring a habit to another habit's permissions.
    if policy.habit != habit:
        raise PolicyError(f"policy {path} is for habit {policy.habit!r}, not {habit!r}")
    return policy
