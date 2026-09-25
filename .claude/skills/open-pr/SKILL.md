---
name: open-pr
description: Verify, push, and open a pull request that follows the repository's PR template and conventions (Conventional Commit title, Safety-Impact declaration, AI involvement). Use when a change on a branch is ready for review.
---

# Open a pull request

This skill never merges or approves. The job ends with a PR link handed to the user.

**In the agent-main loop** (the `agent-loop` skill), the base is `agent-main`: read `agent-main` wherever a step below says `main`, open the PR ready for review (not a draft), start the body with the loop's author note, and set AI involvement to `authored`.

## Steps

1. **Confirm you are not on `main`:** `git symbolic-ref --short HEAD`. Validate the name with `scripts/checks/branch-name.sh`.
2. **Review your own diff** against the base: `git fetch origin && git diff origin/main...HEAD`. Remove debugging leftovers, unrelated changes, and anything resembling a secret or real customer data.
3. **Rebase on the latest main** if it has moved: `git rebase origin/main`. Resolve conflicts carefully; if unsure, stop and ask.
4. **Run the checks:** `make check`. Fix failures before continuing. Do not skip hooks.
5. **Check for safety-critical changes:** `scripts/checks/safety-guard.sh --base origin/main`.
   - If any are reported, run the `safety-reviewer` subagent on the diff and address its findings.
   - Decide the honest `Safety-Impact` value: `neutral`, `tightens`, or `loosens`. If `loosens`, the PR must explain exactly what becomes allowed and why, and must contain nothing else.
6. **Write the PR title** as a Conventional Commit header and validate it: `scripts/checks/commit-message.sh --pr-title "<title>"`.
7. **Write the body** from `.github/pull_request_template.md`. Fill in every section:
   - Summary: what and why, concise.
   - `Closes #<issue>`.
   - Tick the type-of-change boxes that apply.
   - `Safety-Impact: <value>` on its own line.
   - Verification: the commands you actually ran and their outcome. Do not claim checks you did not run.
   - AI involvement: `assisted` for a Claude Code session driven by a user.
8. **Push:** `git push -u origin HEAD` (use `--force-with-lease` only if you rebased an already-pushed branch).
9. **Open the PR as a draft** unless the user asked for ready-for-review:

   ```bash
   gh pr create --draft --base main --title "<title>" --body-file <file>
   ```

10. **Report** the PR URL, the checks status (`gh pr checks`), and anything the reviewer should look at closely.
