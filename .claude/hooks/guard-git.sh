#!/usr/bin/env bash
#
# Claude Code PreToolUse hook for Bash commands.
# Blocks git and gh operations that would bypass the PR-only workflow
# (CONTRIBUTING.md#how-the-rules-are-enforced). Exit code 2 blocks the command
# and shows the message to Claude.
#
# This is a guardrail, not a security boundary: the GitHub ruleset is the boundary.

set -uo pipefail
export LC_ALL=C

input="$(cat)"

if command -v jq >/dev/null 2>&1; then
  cmd="$(printf '%s' "$input" | jq -r '.tool_input.command // empty')"
  cwd="$(printf '%s' "$input" | jq -r '.cwd // empty')"
elif command -v python3 >/dev/null 2>&1; then
  cmd="$(printf '%s' "$input" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("tool_input",{}).get("command",""))')"
  cwd="$(printf '%s' "$input" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("cwd",""))')"
else
  echo "guard-git: neither jq nor python3 found; git guardrails are inactive" >&2
  exit 0
fi

[ -n "$cmd" ] || exit 0
cwd="${cwd:-${CLAUDE_PROJECT_DIR:-.}}"

# Collapse whitespace so patterns are simpler.
cmd="$(printf '%s' "$cmd" | tr '\n\t' '  ' | tr -s ' ')"

block() {
  printf 'Blocked by .claude/hooks/guard-git.sh: %s\n' "$1" >&2
  printf 'See CONTRIBUTING.md and AGENTS.md#hard-rules. Do not try to work around this guardrail; ask the user if you believe it is wrong.\n' >&2
  exit 2
}

# A command segment boundary: start, or one of ; & | ( followed by optional space.
b='(^|[;&|(][ ]*)'
# "git" optionally followed by global options such as -C <dir> or -c <k=v>.
git_cmd="${b}git( -[Cc] [^ ;&|]+)*"
# Rest of the current command segment.
seg='[^;&|]*'

current_branch="$(git -C "$cwd" symbolic-ref --short -q HEAD 2>/dev/null || true)"
has_commits="$(git -C "$cwd" rev-parse --verify --quiet HEAD >/dev/null 2>&1 && echo yes || echo no)"

# ── Hook bypass ───────────────────────────────────────────────────────────
re="${git_cmd} (commit|push|merge|rebase|am)${seg} --no-verify"
if [[ "$cmd" =~ $re ]]; then
  block "--no-verify skips the repository's git hooks."
fi

re="${git_cmd} config${seg}core\.hooksPath"
if [[ "$cmd" =~ $re ]]; then
  # Reading is fine; so is setting it to the repository's hooks directory.
  re_read="${git_cmd} config( --[a-z]+)* (--get|--get-all|get)( --[a-z]+)* core\.hooksPath([ ;&|]|$)"
  re_read_bare="${git_cmd} config core\.hooksPath *([;&|]|$)"
  re_ok="${git_cmd} config( --local)? core\.hooksPath \.githooks([ ;&|]|$)"
  if ! [[ "$cmd" =~ $re_read ]] && ! [[ "$cmd" =~ $re_read_bare ]] && ! [[ "$cmd" =~ $re_ok ]]; then
    block "changing core.hooksPath disables the repository's git hooks."
  fi
fi

# ── Commits on main ───────────────────────────────────────────────────────
re="${git_cmd} commit( |$)"
if [[ "$cmd" =~ $re ]] && [ "$current_branch" = "main" ] && [ "$has_commits" = "yes" ]; then
  block "you are on 'main'. Create a branch first: git switch -c <type>/<issue>-<short-description>"
fi

# ── Pushes ────────────────────────────────────────────────────────────────
re="${git_cmd} push( |$)"
if [[ "$cmd" =~ $re ]]; then
  re_main="${git_cmd} push${seg}[ :/+]main([ ;&|]|$)"
  if [[ "$cmd" =~ $re_main ]]; then
    block "pushing to 'main' is not allowed. Push your branch and open a pull request."
  fi

  re_bare="${git_cmd} push( (-u|--set-upstream|origin))*( *$|[ ]*[;&|])"
  if [[ "$cmd" =~ $re_bare ]] && [ "$current_branch" = "main" ]; then
    block "you are on 'main'; a bare 'git push' would push to main."
  fi

  re_force="${git_cmd} push${seg} (--force|-f)([ ;&|]|$)"
  re_plus="${git_cmd} push${seg} \+[^ ]"
  if [[ "$cmd" =~ $re_force ]] || [[ "$cmd" =~ $re_plus ]]; then
    block "plain force-push is not allowed. Use --force-with-lease on your own branch."
  fi
fi

# ── Merging and approving PRs ─────────────────────────────────────────────
re="${b}gh pr merge( |$)"
if [[ "$cmd" =~ $re ]]; then
  block "merging pull requests is a human decision."
fi

re="${b}gh pr review${seg} (--approve|-a)([ ;&|]|$)"
if [[ "$cmd" =~ $re ]]; then
  block "approving pull requests is a human decision."
fi

# ── Repository protection ─────────────────────────────────────────────────
re="${b}gh api${seg}(rulesets|/protection|/branches/[^ ]+/protection)"
if [[ "$cmd" =~ $re ]]; then
  re_write="${b}gh api${seg} (-X|--method)[ =]?(POST|PUT|PATCH|DELETE)"
  re_fields="${b}gh api${seg} (-f|-F|--field|--raw-field|--input)[ =]"
  if [[ "$cmd" =~ $re_write ]] || [[ "$cmd" =~ $re_fields ]]; then
    block "changing branch protection or rulesets must be done by a repository admin."
  fi
fi

re="${b}(bash |sh |\./)?scripts/bootstrap-github\.sh"
if [[ "$cmd" =~ $re ]] && ! [[ "$cmd" =~ --dry-run ]]; then
  block "scripts/bootstrap-github.sh changes repository settings; a repository admin must run it."
fi

exit 0
