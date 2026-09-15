# pan-galactic-x

A meta-agentic system that creates agentic flows (**lobes**) on demand, versions them in git, and improves them over time — with every change gated by a pull request and human review.

> **Status:** pre-implementation. The architecture is defined; Phase 1 (the Backlog Refiner, built by hand) has not started. See [ARCHITECTURE.md §12](ARCHITECTURE.md#12-build-order).

## Start here

| If you want to… | Read |
|---|---|
| Understand the system | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Contribute (branches, commits, PRs, reviews) | [CONTRIBUTING.md](CONTRIBUTING.md) |
| Work on this repo as an AI agent | [AGENTS.md](AGENTS.md) |
| Understand how humans and AI agents collaborate here | [docs/development/agentic-development.md](docs/development/agentic-development.md) |
| Write or review lobe memory | [docs/development/memory-style-guide.md](docs/development/memory-style-guide.md) |
| See why a decision was made | [docs/adr/](docs/adr/) |
| Report a vulnerability | [SECURITY.md](SECURITY.md) |

## Getting started

```bash
git clone https://github.com/emiralpayar/pan-galactic-refiner.git
cd pan-galactic-refiner
make setup   # installs git hooks and the commit message template
make check   # runs the same convention and lint checks as CI
```

`main` is protected: nobody commits to it directly. Every change is a branch and a pull request — see [CONTRIBUTING.md](CONTRIBUTING.md).

## Repository layout

```text
lobes/              # one folder per lobe: agent, memory, safety policy, evals
adapters/           # system-specific integrations (e.g. Azure DevOps)
safety-layer/       # deterministic write-gating engine (shared)
orchestrator/       # creates new lobes as PRs
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
