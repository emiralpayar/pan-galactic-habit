#!/usr/bin/env bash
#
# Detects changes to safety-critical paths and verifies that the PR declares
# its safety impact (ARCHITECTURE.md §4.2, CONTRIBUTING.md#safety-critical-changes).
#
# Usage:
#   scripts/checks/safety-guard.sh --base <ref> [--head <ref>]
#
# Environment (set by CI; optional locally):
#   PR_BODY     Pull request description. When unset, the Safety-Impact
#               declaration is not checked (local, informational run).
#   PR_AUTHOR   Pull request author login. Dependabot is exempt from the
#               declaration, but its PRs are still labeled and need code owners.
#   GITHUB_OUTPUT, GITHUB_STEP_SUMMARY   Written when present.
#
# Exit codes: 0 = pass, 1 = safety-critical change without a valid declaration, 2 = usage.

set -euo pipefail
export LC_ALL=C

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../lib/conventions.sh
. "$here/../lib/conventions.sh"

base=""
head="HEAD"
while [ $# -gt 0 ]; do
  case "$1" in
    --base) base="${2:-}"; shift 2 ;;
    --head) head="${2:-}"; shift 2 ;;
    *) sed -n '3,17p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//' >&2; exit 2 ;;
  esac
done
[ -n "$base" ] || { fail "--base is required"; exit 2; }

patterns_file="$here/safety-critical-paths.txt"

emit_output() {
  if [ -n "${GITHUB_OUTPUT:-}" ]; then
    echo "$1" >>"$GITHUB_OUTPUT"
  fi
}

summary() {
  if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
    printf '%s\n' "$1" >>"$GITHUB_STEP_SUMMARY"
  fi
}

changed_files="$(git diff --name-only "${base}...${head}")"

matches=""
while IFS= read -r file; do
  [ -n "$file" ] || continue
  while IFS= read -r pattern; do
    case "$pattern" in "" | "#"*) continue ;; esac
    # shellcheck disable=SC2053  # the pattern is intentionally a glob
    if [[ "$file" == $pattern ]]; then
      matches="${matches}${file}"$'\n'
      break
    fi
  done <"$patterns_file"
done <<<"$changed_files"

if [ -z "$matches" ]; then
  emit_output "safety_critical=false"
  ok "No safety-critical paths changed."
  summary "✔ No safety-critical paths changed."
  exit 0
fi

emit_output "safety_critical=true"
warn "Safety-critical paths changed:"
printf '%s' "$matches" | sed 's/^/    /' >&2
summary "### ⚠️ Safety-critical paths changed"
summary ""
# shellcheck disable=SC2016  # the backticks are literal markdown
summary "$(printf '%s' "$matches" | sed 's/^/- `/; s/$/`/')"
summary ""
summary "Code owner approval is required."

if [ "${PR_BODY+set}" != "set" ]; then
  warn "PR_BODY not set; skipping the Safety-Impact declaration check (local run)."
  exit 0
fi

if [ "${PR_AUTHOR:-}" = "dependabot[bot]" ]; then
  ok "Dependabot PR; Safety-Impact declaration not required."
  exit 0
fi

impact="$(printf '%s\n' "$PR_BODY" | tr -d '\r' \
  | sed -n 's/^Safety-Impact:[[:space:]]*\([A-Za-z]*\).*$/\1/p' | head -n 1 \
  | tr '[:upper:]' '[:lower:]')"

case "$impact" in
  neutral | tightens)
    ok "Safety-Impact: $impact"
    summary "Declared **Safety-Impact: ${impact}**."
    exit 0
    ;;
  loosens)
    warn "Safety-Impact: loosens — this PR needs extra scrutiny."
    summary "Declared **Safety-Impact: loosens** — review with extra scrutiny."
    exit 0
    ;;
  none | "")
    fail "Safety-critical paths changed, but the PR description declares 'Safety-Impact: ${impact:-<missing>}'."
    cat >&2 <<EOF

  Add one of these lines to the PR description:
    Safety-Impact: neutral    # touches safety-critical files without changing what is allowed
    Safety-Impact: tightens   # something previously allowed no longer is
    Safety-Impact: loosens    # something previously disallowed now is — explain what and why

  See ${CONTRIBUTING_URL}#safety-critical-changes
EOF
    summary "✖ Missing or \`none\` Safety-Impact declaration."
    exit 1
    ;;
  *)
    fail "Unknown Safety-Impact value '$impact'. Use neutral, tightens, or loosens."
    exit 1
    ;;
esac
