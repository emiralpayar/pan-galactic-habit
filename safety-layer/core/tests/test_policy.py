from pathlib import Path

import pytest
from pydantic import ValidationError

from safety_layer.policy import PolicyError, SafetyPolicy, load_policy

VALID = """\
habit: example-habit
writes:
  - operation: update-record
    fields: [title, body]
budgets:
  per_call: 1
  per_session: 5
  per_time_window:
    limit: 20
    window_minutes: 1440
"""


def _write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "safety-policy.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def _load(tmp_path: Path, text: str) -> SafetyPolicy:
    return load_policy(_write(tmp_path, text), habit="example-habit")


def test_session_may_exceed_a_short_time_window(tmp_path: Path) -> None:
    text = VALID.replace("limit: 20", "limit: 2").replace(
        "window_minutes: 1440", "window_minutes: 5"
    )

    assert _load(tmp_path, text).budgets.per_time_window.limit == 2


def test_valid_policy_loads(tmp_path: Path) -> None:
    policy = _load(tmp_path, VALID)

    assert policy.habit == "example-habit"
    assert policy.budgets.per_time_window.window_minutes == 1440
    assert policy.allows("update-record", "title")


@pytest.mark.parametrize(
    ("operation", "field"),
    [
        ("update-record", "state"),
        ("delete-record", "title"),
        ("UPDATE-RECORD", "title"),
        ("update-record", "Title"),
        ("", ""),
    ],
)
def test_anything_unlisted_is_denied(tmp_path: Path, operation: str, field: str) -> None:
    assert not _load(tmp_path, VALID).allows(operation, field)


def test_policy_without_writes_is_read_only(tmp_path: Path) -> None:
    text = VALID.replace("writes:\n  - operation: update-record\n    fields: [title, body]\n", "")
    policy = _load(tmp_path, text)

    assert policy.writes == ()
    assert not policy.allows("update-record", "title")


def test_policy_is_immutable(tmp_path: Path) -> None:
    policy = _load(tmp_path, VALID)

    with pytest.raises(ValidationError):
        policy.habit = "other-habit"


def test_missing_file_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(PolicyError, match="cannot read"):
        load_policy(tmp_path / "missing.yaml", habit="example-habit")


def test_non_utf8_file_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "safety-policy.yaml"
    path.write_bytes(b"habit: \xff\n")

    with pytest.raises(PolicyError, match="cannot read"):
        load_policy(path, habit="example-habit")


def test_policy_for_another_habit_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(PolicyError, match="not 'other-habit'"):
        load_policy(_write(tmp_path, VALID), habit="other-habit")


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("habit: [unclosed\n", id="malformed"),
        pytest.param(VALID + "---\n" + VALID, id="two-documents"),
        pytest.param(VALID + "habit: other-habit\n", id="duplicate-top-level-key"),
        pytest.param(
            VALID.replace("  per_call: 1\n", "  per_call: 1\n  per_call: 5\n"),
            id="duplicate-nested-key",
        ),
        pytest.param(
            VALID.replace("  per_session: 5\n", "  per_session: &n 5\n").replace(
                "    limit: 20\n", "    limit: *n\n"
            ),
            id="alias",
        ),
        pytest.param(VALID.replace("budgets:\n", "budgets: &b\n"), id="anchor"),
        pytest.param(VALID + "<<: {habit: other-habit}\n", id="merge-key"),
        pytest.param(VALID + "1: one\n", id="non-string-key"),
        pytest.param(VALID.replace("per_session: 5", "per_session: 010"), id="octal-int"),
        pytest.param(VALID.replace("per_session: 5", "per_session: 0b101"), id="binary-int"),
        pytest.param(VALID.replace("per_session: 5", "per_session: 0x5"), id="hex-int"),
        pytest.param(VALID.replace("limit: 20", "limit: 1:30"), id="sexagesimal-int"),
        pytest.param(VALID.replace("limit: 20", "limit: 2_0"), id="underscore-int"),
        pytest.param(VALID.replace("per_call: 1", "per_call: +1"), id="signed-int"),
        pytest.param(VALID.replace("per_call: 1", "per_call: !!int '1'"), id="int-tag"),
        pytest.param(VALID.replace("[title, body]", "!!set {title, body}"), id="set-tag"),
        pytest.param(VALID.replace("[title, body]", "!!seq [title, body]"), id="seq-tag"),
        pytest.param("habit: 2020-13-45\n", id="impossible-date"),
        pytest.param("habit: " + "[" * 5000 + "]" * 5000 + "\n", id="deep-nesting"),
    ],
)
def test_invalid_or_ambiguous_yaml_fails_closed(tmp_path: Path, text: str) -> None:
    with pytest.raises(PolicyError, match="invalid YAML"):
        _load(tmp_path, text)


@pytest.mark.parametrize("text", ["", "- habit: example-habit\n", "just a string\n"])
def test_document_that_is_not_a_mapping_fails_closed(tmp_path: Path, text: str) -> None:
    with pytest.raises(PolicyError, match="must be a mapping"):
        _load(tmp_path, text)


@pytest.mark.parametrize(
    "text",
    [
        pytest.param(VALID.replace("habit: example-habit\n", ""), id="missing-habit"),
        pytest.param(VALID[: VALID.index("budgets:")], id="missing-budgets"),
        pytest.param(VALID + "confirmation_required: false\n", id="unknown-top-level-field"),
        pytest.param(
            VALID.replace("    fields:", "    forbidden: [state]\n    fields:"),
            id="unknown-rule-field",
        ),
        pytest.param(VALID.replace("habit: example-habit", "habit: Example_Habit"), id="habit"),
        pytest.param(VALID.replace("fields: [title, body]", "fields: []"), id="no-fields"),
        pytest.param(VALID.replace("[title, body]", "[title, title]"), id="duplicate-field"),
        pytest.param(VALID.replace("[title, body]", "[title, no]"), id="bool-field"),
        pytest.param(VALID.replace("[title, body]", "['my title']"), id="whitespace-field"),
        pytest.param(VALID.replace("[title, body]", "[title\u200b]"), id="invisible-field"),
        pytest.param(VALID.replace("[title, body]", '["title\\u200b"]'), id="escaped-field"),
        pytest.param(
            VALID.replace("writes:\n", "writes:\n  - operation: update-record\n    fields: [x]\n"),
            id="duplicate-operation",
        ),
        pytest.param(VALID.replace("per_call: 1", "per_call: 0"), id="zero-budget"),
        pytest.param(VALID.replace("per_call: 1", "per_call: -1"), id="negative-budget"),
        pytest.param(VALID.replace("per_call: 1", "per_call: '1'"), id="string-budget"),
        pytest.param(VALID.replace("per_call: 1", "per_call: 1.0"), id="float-budget"),
        pytest.param(VALID.replace("per_call: 1", "per_call: true"), id="bool-budget"),
        pytest.param(VALID.replace("per_call: 1", "per_call: 6"), id="call-over-session"),
    ],
)
def test_invalid_policy_fails_closed(tmp_path: Path, text: str) -> None:
    with pytest.raises(PolicyError, match="invalid policy"):
        _load(tmp_path, text)
