#!/usr/bin/env bash
#
# Applies the repository's GitHub configuration: merge settings, labels, and
# the `protect-main` ruleset from .github/rulesets/protect-main.json.
#
# Requires: gh (authenticated), jq, and ADMIN permission on the repository.
# Rulesets on private repositories owned by a personal account require GitHub Pro
# (or an organization on GitHub Team/Enterprise).
#
# Usage:
#   scripts/bootstrap-github.sh [--dry-run]
#
# Environment:
#   REPO                 owner/name (default: detected from the git remote)
#   REQUIRED_APPROVALS   overrides required_approving_review_count (default: from the JSON)
#
# Safe to re-run: labels are upserted and the ruleset is updated in place.

set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/conventions.sh
. "$here/lib/conventions.sh"

dry_run=false
note=""
if [ "${1:-}" = "--dry-run" ]; then
  dry_run=true
  note=" (dry-run: nothing changed)"
fi

root="$(repo_root)"
ruleset_file="$root/.github/rulesets/protect-main.json"

for tool in gh jq; do
  command -v "$tool" >/dev/null 2>&1 || { fail "$tool is required"; exit 1; }
done

repo="${REPO:-$(gh repo view --json nameWithOwner --jq .nameWithOwner)}"

run() {
  if $dry_run; then
    echo "[dry-run] $*"
  else
    "$@"
  fi
}

is_admin="$(gh api "repos/$repo" --jq '.permissions.admin')"
if [ "$is_admin" != "true" ] && ! $dry_run; then
  fail "You need admin permission on $repo to apply this configuration."
  exit 1
fi

# ── Merge settings ────────────────────────────────────────────────────────
# Squash only; the squash commit uses the PR title and keeps commit messages
# (and therefore Co-Authored-By trailers) in the body.
run gh api --method PATCH "repos/$repo" \
  -F allow_squash_merge=true \
  -F allow_merge_commit=false \
  -F allow_rebase_merge=false \
  -F allow_auto_merge=false \
  -F allow_update_branch=true \
  -F delete_branch_on_merge=true \
  -f squash_merge_commit_title=PR_TITLE \
  -f squash_merge_commit_message=COMMIT_MESSAGES \
  --silent
ok "Merge settings applied to $repo${note}"

# ── Labels ────────────────────────────────────────────────────────────────
label() {
  run gh label create "$1" --repo "$repo" --color "$2" --description "$3" --force
}
label "safety-critical"    "b60205" "Touches a safety-critical path; code owner review required"
label "memory"             "0e8a16" "Changes habit memory"
label "behavior"           "1d76db" "Changes agent, orchestrator, improver, or interface code"
label "docs"               "0075ca" "Documentation"
label "dev-tooling"        "5319e7" "Developer and agent tooling"
label "ci"                 "fbca04" "CI workflows"
label "dependencies"       "0366d6" "Dependency updates"
label "bug"                "d73a4a" "Something is not working"
label "enhancement"        "a2eeef" "New capability or improvement"
label "habit-request"      "c5def5" "Request for a new habit"
label "needs-adr"          "e99695" "A decision must be recorded in an ADR before merging"
label "agent:orchestrator" "bfdadc" "Authored by the Orchestrator Agent"
label "agent:improver"     "bfdadc" "Authored by the Improver Agent"
label "agent:habit"        "bfdadc" "Proposed by a running habit"
ok "Labels upserted${note}"

# ── Ruleset ───────────────────────────────────────────────────────────────
payload="$(cat "$ruleset_file")"
if [ -n "${REQUIRED_APPROVALS:-}" ]; then
  payload="$(printf '%s' "$payload" | jq --argjson n "$REQUIRED_APPROVALS" \
    '(.rules[] | select(.type == "pull_request") | .parameters.required_approving_review_count) = $n')"
fi

name="$(printf '%s' "$payload" | jq -r .name)"
existing_id="$(gh api "repos/$repo/rulesets" --jq ".[] | select(.name == \"$name\") | .id" 2>/dev/null || true)"

if $dry_run; then
  echo "[dry-run] ruleset payload:"
  printf '%s\n' "$payload"
elif [ -n "$existing_id" ]; then
  printf '%s' "$payload" | gh api --method PUT "repos/$repo/rulesets/$existing_id" --input - --silent
  ok "Ruleset '$name' updated (id $existing_id)"
else
  if ! printf '%s' "$payload" | gh api --method POST "repos/$repo/rulesets" --input - --silent; then
    fail "Could not create the ruleset. Private repositories on a free personal account"
    fail "do not support rulesets; upgrade the owner to GitHub Pro or move the repo to an organization."
    exit 1
  fi
  ok "Ruleset '$name' created"
fi

ok "GitHub configuration applied${note}. Verify under Settings → Rules → Rulesets."
