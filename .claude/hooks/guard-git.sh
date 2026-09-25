#!/usr/bin/env bash
#
# Claude Code PreToolUse hook for Bash commands.
# Blocks git and gh operations that would bypass the PR-only workflow
# (CONTRIBUTING.md#how-the-rules-are-enforced). Exit code 2 blocks the command
# and shows the message to Claude.
#
# This is a guardrail, not a security boundary: the GitHub rulesets are the boundary.

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

# Keep the original for checks that must see line breaks, then collapse whitespace so
# patterns are simpler.
raw_cmd="$cmd"
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

# ── Commits on main and agent-main ────────────────────────────────────────
re="${git_cmd} commit( |$)"
if [[ "$cmd" =~ $re ]] && [ "$has_commits" = "yes" ] \
  && { [ "$current_branch" = "main" ] || [ "$current_branch" = "agent-main" ]; }; then
  block "you are on '$current_branch'. Create a branch first: git switch -c <type>/<issue>-<short-description>"
fi

# ── Pushes ────────────────────────────────────────────────────────────────
re="${git_cmd} push( |$)"
if [[ "$cmd" =~ $re ]]; then
  re_main="${git_cmd} push${seg}([ :/+][\"']?|[ :/+][\"']?agent-)main[\"']?([ ;&|]|$)"
  if [[ "$cmd" =~ $re_main ]]; then
    block "pushing to 'main' or 'agent-main' is not allowed. Push your branch and open a pull request."
  fi

  re_all="${git_cmd} push${seg} (--all|--mirror)([ ;&|=]|$)"
  if [[ "$cmd" =~ $re_all ]]; then
    block "pushing every branch at once is not allowed. Push your branch by name."
  fi

  re_bare="${git_cmd} push( (-u|--set-upstream|origin))*( *$|[ ]*[;&|])"
  # "push ... HEAD" names no explicit branch either; it pushes whatever is
  # checked out, same as a bare push.
  re_head="${git_cmd} push( (-u|--set-upstream|origin))* HEAD([ ;&|]|$)"
  if { [[ "$cmd" =~ $re_bare ]] || [[ "$cmd" =~ $re_head ]]; } \
    && { [ "$current_branch" = "main" ] || [ "$current_branch" = "agent-main" ]; }; then
    block "you are on '$current_branch'; this push would push to $current_branch."
  fi

  re_force="${git_cmd} push${seg} (--force|-f)([ ;&|]|$)"
  re_plus="${git_cmd} push${seg} \+[^ ]"
  if [[ "$cmd" =~ $re_force ]] || [[ "$cmd" =~ $re_plus ]]; then
    block "plain force-push is not allowed. Use --force-with-lease on your own branch."
  fi

  # Deleting a remote ref (branch or tag) is never part of the issue -> branch
  # -> PR flow; block it regardless of which branch is current.
  re_delete_flag="${git_cmd} push${seg} (--delete|-d)([ ;&|]|$)"
  re_delete_refspec="${git_cmd} push${seg} :[^ ;&|]+"
  if [[ "$cmd" =~ $re_delete_flag ]] || [[ "$cmd" =~ $re_delete_refspec ]]; then
    block "deleting a remote branch or tag is not allowed."
  fi

  # `git push --receive-pack='sh -c …'` and the ext:: transport both run a command
  # of the pusher's choosing on this machine, so a push rule alone is not a push
  # rule. This is why the Claude GitHub action allowlists its own git-push.sh
  # wrapper instead of `git push`.
  re_exec="${git_cmd} push${seg} (--receive-pack|--exec)[ =]"
  re_transport="${git_cmd} push${seg} (ext|ftp|ftps)::"
  if [[ "$cmd" =~ $re_exec ]] || [[ "$cmd" =~ $re_transport ]]; then
    block "this push form can run an arbitrary command. Push a branch to 'origin' by name."
  fi
fi

# ── Merging and approving PRs ─────────────────────────────────────────────
# Allowed only for a pull request into agent-main, the agent loop's integration
# branch, and only from a loop agent account (ADR 0010). Into main, from a code
# owner's account, or whenever anything cannot be established, it stays a human
# decision. The GitHub rulesets remain the boundary: a loop agent account is not a
# code owner, so its approval can never satisfy main's code owner review.
#
# Recognized forms (env prefixes, `command gh`, absolute paths, quoted or escaped
# words, a second line) must match the one allowed shape, or they are blocked. A
# script, curl, or another client can still reach the API; this is a guardrail.
loop_merge_allowed() {
  local verb="$1" rest selector option login owners base
  # One plain line: no line breaks, chaining, subshells, substitutions, quoting,
  # escapes, or globs whose effect the checks below would not see.
  case "$raw_cmd" in
    *$'\n'* | *$'\r'*) return 1 ;;
  esac
  case "$cmd" in
    *';'* | *'&'* | *'|'* | *'('* | *')'* | *'`'* | *'$'* | *'<'* | *'>'* \
      | *"'"* | *'"'* | *\\* | *'{'* | *'}'* | *'*'* | *'?'* | *'~'* | *'='*) return 1 ;;
  esac
  [[ "$cmd" =~ ^\ *gh\ pr\ ${verb}\ ([^ ]+)(.*)$ ]] || return 1
  selector="${BASH_REMATCH[1]}"
  rest="${BASH_REMATCH[2]}"
  [[ "$selector" =~ ^([0-9]+|https://github\.com/emiralpayar/pan-galactic-habit/pull/[0-9]+)$ ]] || return 1
  # Only the options the loop needs; anything else (--admin, -R, --auto, -ab, ...) is refused.
  # Word splitting is intended here, and globs were refused above.
  # shellcheck disable=SC2086
  set -- $rest
  while [ $# -gt 0 ]; do
    option="$1"
    shift
    case "$verb:$option" in
      merge:--squash | merge:--merge | review:--approve) ;;
      review:--body-file)
        [ $# -gt 0 ] && [[ "$1" != -* ]] || return 1
        shift
        ;;
      *) return 1 ;;
    esac
  done
  # A code owner's approval counts on main; the loop runs only on agent accounts.
  login="$(cd "$cwd" 2>/dev/null && gh api user --jq .login 2>/dev/null)" || return 1
  [ -n "$login" ] || return 1
  owners="$(git -C "$cwd" show origin/main:.github/CODEOWNERS 2>/dev/null)" || return 1
  [ -n "$owners" ] || return 1
  owners=" $(printf '%s' "$owners" | tr '[:upper:]' '[:lower:]' | tr '\n\t' '  ') "
  [[ "$owners" == *" @$(printf '%s' "$login" | tr '[:upper:]' '[:lower:]') "* ]] && return 1
  base="$(cd "$cwd" 2>/dev/null && gh pr view "$selector" --json baseRefName --jq .baseRefName 2>/dev/null)" || return 1
  [ "$base" = "agent-main" ]
}

# Detection runs on a copy without quotes and backslashes, so `"merge"`, `mer''ge`,
# and `m\erge` are recognized; the allowed shape above refuses them anyway.
norm="$(printf '%s' "$cmd" | tr -d "'\"\\\\")"
w='(^|[^a-z0-9_-])'

re_merge="${w}pr merge( |$)"
if [[ "$norm" =~ $re_merge ]] && ! loop_merge_allowed merge; then
  block "merging is allowed only from a loop agent account, for a pull request into agent-main, as a single plain command: gh pr merge <number> --squash (or --merge for a sync). Into main it is a human decision."
fi

re_approve="${w}pr review .*( --approve([ =]|$)| -[A-Za-z]*a[A-Za-z]*( |$))"
if [[ "$norm" =~ $re_approve ]] && ! loop_merge_allowed review; then
  block "approving is allowed only from a loop agent account, for a pull request into agent-main, as a single plain command: gh pr review <number> --approve --body-file <file>. For main it is a human decision."
fi

# Retargeting a PR could carry an approval from agent-main to main.
re="${w}pr edit .*( --base| -[A-Za-z]*B)"
if [[ "$norm" =~ $re ]]; then
  block "changing a pull request's base branch is not allowed; open a new pull request instead."
fi

# The same operations through the API, which the checks above would not see.
re="${w}api .*(pulls/[^ ]+/merge|mergePullRequest|enablePullRequestAutoMerge|addPullRequestReview|submitPullRequestReview|updatePullRequest)"
re_pull="${w}api( .*)? [^ ]*pulls/[0-9]+(/reviews)?( |$)"
re_write="${w}api( .*)? ((-X|--method)[ =]?(POST|PUT|PATCH)|(-f|-F|--field|--raw-field|--input)[ =]?)"
re_graphql_file="${w}api graphql.*( (-F|--field) [a-z_]+=@| --input)"
if [[ "$norm" =~ $re ]] || { [[ "$norm" =~ $re_pull ]] && [[ "$norm" =~ $re_write ]]; } \
  || [[ "$norm" =~ $re_graphql_file ]]; then
  block "changing, merging, or reviewing a pull request through the API is not allowed; use gh pr merge or gh pr review."
fi

# Ways to run gh commands the checks above would not recognize, or to take its token.
re="${w}gh (alias (set|import)|extension (install|upgrade|create)|ext (install|upgrade|create)|auth token)( |$)"
if [[ "$norm" =~ $re ]] || [[ "$norm" == *api.github.com* ]]; then
  block "gh aliases, extensions, the raw token, and direct API URLs are not allowed; use gh pr and gh issue commands."
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
