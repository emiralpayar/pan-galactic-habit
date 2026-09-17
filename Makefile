.DEFAULT_GOAL := help
SHELL := /usr/bin/env bash

SHELL_SCRIPTS := $(wildcard scripts/*.sh scripts/checks/*.sh scripts/lib/*.sh .claude/hooks/*.sh) \
                 $(wildcard .githooks/*)

.PHONY: help
help: ## List available targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

.PHONY: setup
setup: ## One-time local setup: git hooks, commit template, git defaults
	@scripts/setup-dev.sh

.PHONY: check
check: check-branch lint typecheck test imports ## Run all local checks (same as CI where possible)

.PHONY: check-branch
check-branch: ## Validate the current branch name
	@scripts/checks/branch-name.sh

.PHONY: lint
lint: lint-md lint-sh lint-py ## Run all linters

.PHONY: lint-md
lint-md: ## Lint markdown with markdownlint-cli2
	@command -v npx >/dev/null || { echo "npx not found: install Node.js"; exit 1; }
	@npx --yes markdownlint-cli2@0

.PHONY: lint-sh
lint-sh: ## Lint shell scripts with shellcheck
	@command -v shellcheck >/dev/null || { echo "shellcheck not found: https://github.com/koalaman/shellcheck#installing"; exit 1; }
	@shellcheck $(SHELL_SCRIPTS)

.PHONY: sync
sync: ## Install the pinned Python and every workspace package from uv.lock
	@command -v uv >/dev/null || { echo "uv not found: https://docs.astral.sh/uv/getting-started/installation/"; exit 1; }
	@uv sync --locked --all-packages --quiet

.PHONY: lint-py
lint-py: sync ## Lint Python and check its formatting with ruff
	@uv run --locked --all-packages ruff check
	@uv run --locked --all-packages ruff format --check

.PHONY: typecheck
typecheck: sync ## Type-check Python with mypy --strict
	@uv run --locked --all-packages mypy

.PHONY: test
test: sync ## Run Python tests with pytest
	@uv run --locked --all-packages pytest

.PHONY: imports
imports: sync ## Check import-linter contracts (the boundary check, ARCHITECTURE.md §4.2)
	@uv run --locked --all-packages lint-imports

.PHONY: safety-guard
safety-guard: ## List safety-critical changes versus origin/main
	@scripts/checks/safety-guard.sh --base origin/main

.PHONY: adr
adr: ## Create a new ADR: make adr title="short decision title"
	@test -n "$(title)" || { echo 'Usage: make adr title="short decision title"'; exit 2; }
	@scripts/new-adr.sh "$(title)"
