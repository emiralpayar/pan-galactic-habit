#!/usr/bin/env bash
#
# One-time local setup for a fresh clone. Safe to re-run.
# Usage: scripts/setup-dev.sh   (or: make setup)

set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/conventions.sh
. "$here/lib/conventions.sh"

root="$(repo_root)"
cd "$root"

git config core.hooksPath .githooks
chmod +x .githooks/* scripts/*.sh scripts/checks/*.sh .claude/hooks/*.sh
ok "Git hooks installed from .githooks/"

git config commit.template .gitmessage
ok "Commit message template set"

git config fetch.prune true
git config pull.ff only
git config push.autoSetupRemote true
ok "Git defaults set (fetch.prune, pull.ff=only, push.autoSetupRemote)"

missing=""
for tool in gh jq shellcheck npx; do
  command -v "$tool" >/dev/null 2>&1 || missing="$missing $tool"
done
if [ -n "$missing" ]; then
  warn "Optional tools not found:${missing}"
  warn "  gh: PRs from the terminal · jq: Claude Code hook · shellcheck, npx: make check"
fi

if [ ! -f .env ] && [ -f .env.example ]; then
  warn "No .env found. Copy .env.example to .env when you need local credentials."
fi

ok "Setup complete. Next: read CONTRIBUTING.md, then 'make check'."
