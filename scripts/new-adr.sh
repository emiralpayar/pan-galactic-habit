#!/usr/bin/env bash
#
# Creates the next numbered ADR from docs/adr/0000-template.md.
# Usage: scripts/new-adr.sh "short decision title"   (or: make adr title="...")

set -euo pipefail
export LC_ALL=C

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/conventions.sh
. "$here/lib/conventions.sh"

title="${1:-}"
[ -n "$title" ] || { fail 'Usage: scripts/new-adr.sh "short decision title"'; exit 2; }

adr_dir="$(repo_root)/docs/adr"

last="$(find "$adr_dir" -maxdepth 1 -name '[0-9][0-9][0-9][0-9]-*.md' -exec basename {} \; \
  | sort | tail -n 1 | cut -c1-4)"
next="$(printf '%04d' $((10#${last:-0} + 1)))"

slug="$(printf '%s' "$title" | tr '[:upper:]' '[:lower:]' \
  | sed -e 's/[^a-z0-9]\{1,\}/-/g' -e 's/^-//' -e 's/-$//')"
file="$adr_dir/${next}-${slug}.md"

sed -e "s/^# NNNN\. Title$/# ${next}. ${title}/" \
  -e "s/^- \*\*Date:\*\* YYYY-MM-DD$/- **Date:** $(date +%Y-%m-%d)/" \
  "$adr_dir/0000-template.md" >"$file"

ok "Created ${file#"$(repo_root)"/}"
echo "Remember to add it to docs/adr/README.md." >&2
