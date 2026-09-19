# pan-galactic-habit

A meta-agentic system that creates agentic flows (**habits**) on demand, versions them in git, and improves them over time — with every change gated by a pull request and human review.

> **Status:** Phase 1 in progress — the Backlog Refiner, built without the habit template. Progress is tracked in [#13](https://github.com/emiralpayar/pan-galactic-habit/issues/13). See [ARCHITECTURE.md §12](ARCHITECTURE.md#12-build-order).

## Start here

| If you want to… | Read |
|---|---|
| Understand the system | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Contribute (branches, commits, PRs, reviews) | [CONTRIBUTING.md](CONTRIBUTING.md) |
| Work on this repo as an AI agent | [AGENTS.md](AGENTS.md) |
| Understand how humans and AI agents collaborate here | [docs/development/agentic-development.md](docs/development/agentic-development.md) |
| Write or review habit memory | [docs/development/memory-style-guide.md](docs/development/memory-style-guide.md) |
| See why a decision was made | [docs/adr/](docs/adr/) |
| Report a vulnerability | [SECURITY.md](SECURITY.md) |

## Getting started

```bash
git clone https://github.com/emiralpayar/pan-galactic-habit.git
cd pan-galactic-habit
make setup   # installs git hooks and the commit message template
make check   # runs the same convention and lint checks as CI
```

`main` is protected: nobody commits to it directly. Every change is a branch and a pull request — see [CONTRIBUTING.md](CONTRIBUTING.md).

## Repository layout

```text
habits/             # one folder per habit: agent, memory, safety policy, evals
adapters/           # system-specific integrations (e.g. Azure DevOps)
safety-layer/       # deterministic write-gating engine (shared)
orchestrator/       # creates new habits as PRs
improver/           # proposes improvements as PRs
interface/          # chat interface
deploy/             # container build and deployment
docs/               # ADRs and development guides
scripts/            # convention checks and repository tooling
.github/            # CI workflows, CODEOWNERS, templates, rulesets
.githooks/          # local git hooks (installed by `make setup`)
.claude/            # Claude Code settings, hooks, skills, and subagents
```

Each top-level component has a `README.md` describing its responsibility and the rules for changing it.
