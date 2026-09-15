#!/usr/bin/env bash
#
# Validates a commit message or PR title against Conventional Commits,
# as defined in CONTRIBUTING.md#commit-messages.
#
# Usage:
#   scripts/checks/commit-message.sh <file>                # commit-msg hook
#   scripts/checks/commit-message.sh --message "<text>"    # a full commit message
#   scripts/checks/commit-message.sh --pr-title "<text>"   # a PR title

set -euo pipefail
export LC_ALL=C

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../lib/conventions.sh
. "$here/../lib/conventions.sh"

usage() {
  sed -n '3,10p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//' >&2
}

mode="message"
case "${1:-}" in
  --pr-title)
    mode="pr-title"
    text="${2:-}"
    ;;
  --message)
    text="${2:-}"
    ;;
  -h | --help | "")
    usage
    exit 2
    ;;
  *)
    text="$(cat "$1")"
    ;;
esac

# Drop everything below git's scissors line (commit --verbose) and comment lines.
text="$(printf '%s\n' "$text" | sed '/^# -\{24\} >8 -\{24\}$/,$d' | grep -v '^#' || true)"
# Drop leading blank lines.
text="$(printf '%s\n' "$text" | sed '/./,$!d')"

header="$(printf '%s\n' "$text" | sed -n '1p' | tr -d '\r')"
second_line="$(printf '%s\n' "$text" | sed -n '2p' | tr -d '\r')"
label="Commit message"
[ "$mode" = "pr-title" ] && label="PR title"

explain() {
  fail "$label: $1"
  cat >&2 <<EOF

  Got:      ${header}
  Expected: <type>(<scope>)!: <subject>

  Examples:
    feat(safety-layer): enforce per-session write budgets
    fix(backlog-refiner): stop suggesting criteria for closed items
    docs: add adr for trunk-based development

  <type>:  ${CONVENTIONAL_TYPES}
  <scope>: optional; one of: $(allowed_scopes | tr '\n' ' ')
  Subject: imperative, lowercase first letter, no trailing period.
  Header:  ${HEADER_MAX_LENGTH} characters maximum.

  See ${CONTRIBUTING_URL}#commit-messages
EOF
  exit 1
}

if [ -z "$header" ]; then
  explain "is empty."
fi

# Tool-generated messages accepted as-is.
if [[ "$header" =~ ^Revert\ \".+\"$ ]]; then
  ok "$label is a generated revert."
  exit 0
fi
if [ "$mode" = "message" ]; then
  if [[ "$header" =~ ^(fixup|squash|amend)!\  ]]; then
    ok "$label is a fixup; it will be squashed."
    exit 0
  fi
  if [[ "$header" =~ ^Merge\  ]]; then
    ok "$label is a merge commit."
    exit 0
  fi
fi

types="$(types_regex)"
header_regex="^(${types})(\\(([a-z0-9-]+)\\))?(!)?: (.+)$"

if ! [[ "$header" =~ $header_regex ]]; then
  explain "header does not match the Conventional Commits format."
fi

scope="${BASH_REMATCH[3]}"
subject="${BASH_REMATCH[5]}"

if [ "${#header}" -gt "$HEADER_MAX_LENGTH" ]; then
  explain "header is ${#header} characters; the maximum is ${HEADER_MAX_LENGTH}."
fi

if [ -n "$scope" ] && ! is_allowed_scope "$scope"; then
  explain "unknown scope '${scope}'."
fi

if [[ "$subject" =~ ^[A-Z] ]]; then
  explain "subject must start with a lowercase letter."
fi

if [[ "$subject" =~ ^[[:space:]] ]]; then
  explain "subject must not start with whitespace."
fi

if [[ "$subject" =~ \.$ ]]; then
  explain "subject must not end with a period."
fi

if [ "$mode" = "message" ] && [ -n "$second_line" ]; then
  explain "the header must be followed by a blank line before the body."
fi

ok "$label follows Conventional Commits."
