# shellcheck shell=bash
# shellcheck disable=SC2034  # variables are used by the scripts that source this file
#
# Single source of truth for branch, commit, and PR title conventions.
# Documented in CONTRIBUTING.md — keep both in sync.
# Must stay compatible with bash 3.2 (macOS default).

CONVENTIONAL_TYPES="feat fix docs refactor perf test build ci chore revert"

# Scopes that are not derived from directory names.
FIXED_SCOPES="repo dev ci deps docs agent-runtime safety-layer adapters orchestrator improver chat evals deploy"

# Autonomous agents that may author branches under agent/<agent>/...
AGENT_NAME_REGEX='(orchestrator|improver|habit-[a-z0-9]+(-[a-z0-9]+)*)'

SLUG_REGEX='[a-z0-9]+(-[a-z0-9]+)*'

HEADER_MAX_LENGTH=72
BRANCH_MAX_LENGTH=80

CONTRIBUTING_URL="CONTRIBUTING.md"

repo_root() {
  git rev-parse --show-toplevel
}

# "feat|fix|docs|..."
types_regex() {
  echo "$CONVENTIONAL_TYPES" | tr ' ' '|'
}

# Fixed scopes plus every habit and adapter directory name, one per line.
allowed_scopes() {
  local root dir
  root="$(repo_root)"
  echo "$FIXED_SCOPES" | tr ' ' '\n'
  for dir in "$root"/habits/*/ "$root"/adapters/*/; do
    [ -d "$dir" ] && basename "$dir"
  done
}

is_allowed_scope() {
  # Not `allowed_scopes | grep -q`: grep exits on the first match and, with
  # pipefail, the resulting SIGPIPE would turn a match into a failure.
  local scopes
  scopes="$(allowed_scopes)"
  printf '%s\n' "$scopes" | grep -qxF -- "$1"
}

# Colored output only when writing to a terminal.
if [ -t 2 ]; then
  C_RED=$'\033[31m'
  C_GREEN=$'\033[32m'
  C_YELLOW=$'\033[33m'
  C_RESET=$'\033[0m'
else
  C_RED=""
  C_GREEN=""
  C_YELLOW=""
  C_RESET=""
fi

fail() {
  printf '%s✖ %s%s\n' "$C_RED" "$1" "$C_RESET" >&2
}

warn() {
  printf '%s! %s%s\n' "$C_YELLOW" "$1" "$C_RESET" >&2
}

ok() {
  printf '%s✔ %s%s\n' "$C_GREEN" "$1" "$C_RESET" >&2
}
