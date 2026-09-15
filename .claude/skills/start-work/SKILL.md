---
name: start-work
description: Start work on a GitHub issue or task by syncing main and creating a branch that follows the repository's naming conventions. Use when beginning any new change in this repository.
---

# Start work

Create a correctly named branch from an up-to-date `main`.

## Steps

1. **Identify the issue.** If the user gave an issue number, read it with `gh issue view <number>`. If there is no issue and the change is non-trivial, ask whether to create one before continuing.
2. **Check the working tree** with `git status`. If there are uncommitted changes, stop and ask the user what to do with them — never stash or discard them silently.
3. **Choose the type** from the Conventional Commit types: `feat` `fix` `docs` `refactor` `perf` `test` `build` `ci` `chore` `revert`. Pick the one that will describe the eventual PR title.
4. **Build the branch name:** `<type>/<issue>-<short-description>`, or `<type>/<short-description>` without an issue. Lowercase kebab-case, a few words, 80 characters maximum.
5. **Validate it:** `scripts/checks/branch-name.sh <name>`.
6. **Create the branch from the latest main:**

   ```bash
   git fetch origin
   git switch -c <name> origin/main
   ```

   If `origin/main` does not exist yet (brand-new repository), tell the user the repository must be bootstrapped first.
7. **Read before editing:** the `README.md` of each component you expect to change, and the relevant sections of `ARCHITECTURE.md`.
8. **Report** the branch name and a short plan to the user.

## Rules

- Never start work on `main`.
- One branch per concern. If the task mixes concerns, propose splitting it.
