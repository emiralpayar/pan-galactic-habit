# CLAUDE.md

@AGENTS.md

## Claude Code specifics

- **Guardrail hook.** `.claude/hooks/guard-git.sh` runs before every Bash command and blocks committing on `main`, pushing to `main`, force-pushing, `--no-verify`, merging or approving PRs, and changing branch protection. If it blocks you, change your approach; do not try to work around it.
- **Skills** (in `.claude/skills/`):
  - `start-work` — create a correctly named branch from an issue.
  - `open-pr` — run checks, push, and open a PR that follows the template.
  - `new-adr` — record an architecture decision.
  - `new-habit` — scaffold a habit following ARCHITECTURE.md §5.
- **Subagents** (in `.claude/agents/`):
  - `safety-reviewer` — review any change that touches a safety-critical path before opening the PR.
  - `architecture-reviewer` — check a change against ARCHITECTURE.md principles.
- **Personal settings** go in `.claude/settings.local.json` and `CLAUDE.local.md`; both are gitignored.
- **Parallel sessions:** use a separate git worktree per session so branches never collide (see [docs/development/agentic-development.md](docs/development/agentic-development.md#parallel-sessions)).
