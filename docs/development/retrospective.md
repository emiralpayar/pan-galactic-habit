# Retrospective: building pan-galactic-habit with agents

> **Status:** the project is closed and obsolete as of 2026-10-07. This document records what the two maintainers (@emiralpayar and @MGokcay) and their AI agents learned. It covers the repository structure, the guardrails, AI-assisted development, and the autonomous agent loop, for whoever starts the next project. The figures come from the GitHub history up to that date.

**Contents**

1. [Summary](#1-summary)
2. [By the numbers](#2-by-the-numbers)
3. [Repository structure and documentation](#3-repository-structure-and-documentation)
4. [Guardrails and the safety process](#4-guardrails-and-the-safety-process)
5. [AI-assisted development](#5-ai-assisted-development)
6. [The autonomous loop on agent-main](#6-the-autonomous-loop-on-agent-main)
7. [Two maintainers and GitHub's rules](#7-two-maintainers-and-githubs-rules)
8. [Incidents](#8-incidents)
9. [Recommendations for the next project](#9-recommendations-for-the-next-project)
10. [Timeline](#10-timeline)

---

## 1. Summary

pan-galactic-habit was meant to be a meta-agentic system: "habits" (agentic flows) created on request, versioned in git, and gated by a deterministic Safety Layer for every write to an external system. Phase 1 was to build the first habit, the Backlog Refiner for Azure DevOps, by hand ([#13](https://github.com/emiralpayar/pan-galactic-habit/issues/13)).

In eleven active days (2026-09-15 to 2026-09-26), two maintainers working with Claude Code built:

- **The groundwork.** An architecture document, nine ADRs, a fully guarded repository, and CI.
- **Parts of Phase 1.** The Safety Policy loader, the Azure DevOps adapter's read path, the Agent Runtime with a Claude backend, the Backlog Refiner's memory, and write validation.
- **An autonomous loop.** Two Claude Code sessions reviewed, approved, and merged each other's work on an `agent-main` branch ([ADR 0010](../adr/0010-development-agents-integrate-on-an-agent-main-branch.md)).

**Phase 1's exit criteria were not met.** The Backlog Refiner never refined a work item end to end. Still missing were the chat interface ([#44](https://github.com/emiralpayar/pan-galactic-habit/issues/44)), write budgets (#54, open), Write Confirmation, the Operational Store, and the end-to-end run.

The headline lessons, explained in the sections below:

1. **Governance outgrew the product.** Two thirds of merged PRs were about process, and the repository has about three lines of rules, docs, hooks, and workflows for every line of product code.
2. **Controls that live on the server held. Controls that live in prose or regexes leaked.** The GitHub rulesets never failed. The Claude Code hook needed three rounds of bypass fixes, and the loop's written protocol never converged.
3. **Agents are good adversarial reviewers.** Most real defects were found by a separate agent with a reviewer's brief and the instruction to prove each claim (sections [5.4](#54-reviews-by-separate-agents-found-real-defects) and [6.4](#64-what-worked)).
4. **An autonomous loop is a distributed system.** It stalled whenever one side stopped, and nothing noticed.
5. **Identity is the real control for agents.** A token cannot be scoped to a branch. What an agent can do is decided by which account it runs as.

## 2. By the numbers

| Measure | Value |
|---|---|
| Active period | 2026-09-15 to 2026-09-26 (11 days) |
| Commits on `main` / extra commits on `agent-main` | 29 / 6 |
| Merged PRs | 31 |
| ... about process (CI, docs, guardrails, tooling, ADRs) | 20 PRs, +2,526 / −447 lines |
| ... about the product | 7 PRs, +4,204 / −68 lines |
| ... dependency bumps and syncs | 3 + 1 |
| PRs spent getting the Claude GitHub workflow to run | 8 (#6, #15, #25, #26, #27, #28, #29, #37) |
| Reviews posted | 49 |
| Median time from opening to merge | 2.1 hours (longest: #39, 97.7 hours) |
| Product source / product tests on `agent-main` | ~1,350 / ~1,850 lines of Python |
| Markdown / scripts and hooks / workflows | ~2,700 / ~1,000 / ~480 lines |
| Loop PRs into `agent-main` | 7: four merged, one closed as a duplicate, three left open |

The ratio is the most telling number. Most PRs, and most lines that are not tests, went into how to build rather than into what was being built.

## 3. Repository structure and documentation

### 3.1 What worked

- **One source of truth with a strict order.** The order was ARCHITECTURE.md, then CONTRIBUTING.md, then the ADRs, then each component's README. AGENTS.md said this explicitly, and agents followed it. They cited sections in reviews (for example "ARCHITECTURE.md §5.2", "invariant 2"), and when a request conflicted with the architecture they stopped and said so instead of working around it. Decisions and the docs that describe them stayed in sync, because the rule "docs change in the same PR" was enforced by review, not just stated.
- **Component READMEs with invariants.** `safety-layer/README.md` listed invariants that "must be covered by tests": no LLM calls, deny by default, fail closed. That gave reviewers, human or agent, a checklist they could verify mechanically. Many review findings were phrased as violations of a numbered invariant, which made them easy to accept or reject.
- **ADRs as the place for "why".** Recording the stack decisions (ADRs 0003–0005) and the deviation in ADR 0009 kept later sessions from reopening settled questions. Agents treated an accepted ADR as binding.
- **Import contracts** (import-linter) made architectural boundaries, such as "the Safety Layer imports no HTTP client", a CI failure instead of a review comment.
- **Conventions shared by hooks and CI** (`scripts/checks/`). The same script validated branch names and commit messages locally and in CI, so agents got the same answer in both places.

### 3.2 What didn't

- **Too much structure before the first feature.** Before any product code there were placeholder READMEs for components that never got built (`orchestrator/`, `improver/`, `interface/`), a habit template, an eval harness design, and a memory style guide. Every rename touched dozens of files ("lobe" → "habit", #8: 39 files).
- **Docs that restate each other drift.** The rule "agents never approve or merge" appeared in ARCHITECTURE.md (four places), AGENTS.md, CONTRIBUTING.md (three places), SECURITY.md, the guide, a subagent definition, and the hook. Changing it for ADR 0010 meant editing all of them. The architecture review still found SECURITY.md and §1 out of date, and an earlier review had found an ARCHITECTURE.md sentence that a previous PR left stale.
- **ADR numbering collides across parallel PRs.** ADR 0009 was reserved by an open PR (#39) while ADR 0010 merged first, and the ADR index then had a merge conflict. Numbers assigned at merge time, or one file per ADR without a hand-maintained index, would avoid this.
- **"Proposed" vs "Accepted" ADRs** needed their own fix (#17/#18), and two ADRs still say "Proposed". Process artifacts need their own maintenance.

## 4. Guardrails and the safety process

### 4.1 What worked

- **Safety-critical paths as data.** `scripts/checks/safety-critical-paths.txt` drives the CI safety guard, which requires an honest `Safety-Impact:` line (`none`, `neutral`, `tightens`, or `loosens`). The list is mirrored in CODEOWNERS. Authors had to say whether a change loosens a control, and reviewers argued about the value. Several reviews corrected it, for example from `tightens` to `neutral`.
- **Server-side rulesets were the one boundary that never failed.** `main` required a code-owner approval, the last push approved by someone else, and squash-only merges, with no bypass actors. Every bypass found in review stopped at the ruleset, and agents never got a change into `main` without a human approval.
- **Deny by default and fail closed, tested.** The policy loader rejects duplicate keys, YAML anchors, and non-decimal integers. The write validator rejects payloads that are well-typed but wrong. The adapter refuses redirects. These were written as tests, and agent reviewers probed them with crafted inputs (section [6.4](#64-what-worked)).
- **Testing the guard hook itself.** Once the hook became the control that allows agent merges, `tests/test_guard_hook.py` (68 cases) turned every bypass found in review into a regression test that runs in CI.

### 4.2 What didn't

- **A regex hook is an arms race.** `.claude/hooks/guard-git.sh` inspects shell text. Three review rounds found ways past it:
  - a newline between two commands,
  - quoted or attached options (`'--admin'`, `-Rother/repo`),
  - `--approve=true`, short-flag clusters (`-ab`), and quoted words (`gh pr "merge"`),
  - `gh alias`, `gh api` writes to `pulls/<n>`, GraphQL mutations read from a file, retargeting a PR with `gh pr edit --base`,
  - and finally `curl` with a token, which no regex can close.

  Each fix also added false positives: the hook blocked commit messages and test files that merely mentioned the command. A hook is good UX, because it fails early with a clear message. It is not a security boundary, and the docs had to keep saying so.
- **The hook comes from the checked-out branch.** A session on `agent-main` runs whatever hook version is on that branch, so agents can change their own guardrail with a merged PR. Only a user-level copy, or a server-side control, avoids this.
- **Local-only denies hide behavior.** `.claude/settings.json` still denied `gh pr merge` after the hook was changed to allow it on `agent-main`. Sessions would have been pushed towards `gh api` instead. Allow and deny rules in two files have to be reviewed together.
- **Repository-wide settings leak across branches.** Auto-merge and merge commits are repository settings, not branch settings. Turning on auto-merge for `agent-main` would have let an approval of a PR into `main` merge it at once. The safety review caught it before it shipped.

## 5. AI-assisted development

### 5.1 What worked

- **AGENTS.md hard rules, backed by a hook and the ruleset.** Sessions refused to commit to `main`, to approve, to merge, or to bypass hooks. When blocked, they stopped and reported instead of finding another route, as the hook's message asks. This held even when a maintainer asked a session to merge directly.
- **Skills for the repetitive workflow** (`start-work`, `open-pr`, `new-adr`) kept branch names, PR templates, and the `Safety-Impact` declaration consistent across both maintainers' sessions.
- **Attribution.** The `Co-Authored-By:` trailer, the `AI involvement` field, and later the loop's author note made it clear afterwards who wrote what.

### 5.2 What didn't

- **The Claude GitHub app took eight PRs to run** (bubblewrap, socat, user namespaces, permission modes, edit rules). The sandbox, the permission model, and the workspace trust interact in ways only discovered by trial in CI. Each fix was a safety-critical PR with a full review. Budget for this up front, or start with a simpler integration.
- **The automatic Claude review is advisory, and sometimes wrong.** On #57 it claimed that a section was missing from the PR when it was there; it had apparently read another version of the file. Its findings were useful elsewhere, for example on memory style (#55). A clean or a damning bot review still needs checking.
- **"Is this PR OK?" is not a review.** The first pass of this session's review only looked at CI and the bot's comment. A maintainer had to ask explicitly for a review against the repository's rules, which then found blocking problems in both open PRs. The instruction has to name the standard: the rules, the invariants, the ADRs.

### 5.3 Environment coupling

The Agent Runtime refuses to start when unexpected `CLAUDE_CODE_*` variables carrying credentials are set (ADR 0009). A Claude Code session sets `CLAUDE_CODE_MESSAGING_TOKEN` for itself, so `make check` failed **inside every agent session** while passing in CI (#59, #60). A control that reads the environment will see the agent's own environment. Tests for such controls must create their own subprocess environment.

### 5.4 Reviews by separate agents found real defects

Running the `safety-reviewer` and `architecture-reviewer` subagents before opening a PR, with a brief to verify claims rather than trust them, found these issues:

| PR | Found by a separate reviewing agent |
|---|---|
| #39 Agent Runtime | `BUN_OPTIONS` could preload code into the CLI (it runs on Bun, not Node), proven with a marker file. Provider switches and credential variables were missing from the deny-list. `ClaudeRuntime.run` had no tests. A missing `tools` key failed open. |
| #43 memory | The "good" example invented facts its own rule forbids. Another "good" example broke the rule beside it. Rules were duplicated across files. |
| #46 loop setup | Promotion and sync PRs failed the commit-message check permanently. SECURITY.md classed the new behavior as a vulnerability. Repository-wide auto-merge leaked to `main`. The settings deny pushed sessions towards `gh api`. Three rounds of hook bypasses. |

The pattern: give the reviewer a different role from the author, the repository's standards, and an instruction to reproduce each claim. A self-review by the authoring session caught far less.

## 6. The autonomous loop on agent-main

### 6.1 Design

ADR 0010 and the `agent-loop` skill:

- **Branches.** `main` stayed human-gated. Two Claude Code sessions, each under its own **agent account** (a write collaborator, not a code owner), worked on `agent-main`. Each session opened its own issues and PRs, and reviewed, approved, and merged the other's.
- **Promotion.** Work reached `main` only through a promotion PR reviewed by a human, followed by a sync PR back into `agent-main`.
- **Where the boundary was.** Because the agent accounts are not code owners, a session could not approve into `main` even after getting past the hook. The ruleset, not the hook, was the boundary.

The design went through three identity models in one day:

1. bot accounts,
2. the maintainers' own accounts with an author note,
3. per-maintainer agent accounts.

The second was dropped once it was clear that a token cannot be scoped to a branch. A session on a code owner's account could give a valid approval into `main`, and only the hook would stop it.

### 6.2 What happened

The loop ran from 2026-09-25 17:29 UTC to 2026-09-26 14:37 UTC.

| Outcome | PRs |
|---|---|
| Merged by the loop | #48 (read cap), #53 (write validation), #58 (sync from `main`) |
| Merged by a maintainer (`needs-human`, because it loosens) | #52 (WIQL query) |
| Closed as a duplicate | #55 (same work as #43) |
| Left open | #54 (budgets, never reviewed), #57 (the discussion protocol, five review rounds), #60 (the test environment fix) |

### 6.3 Reading the open PRs

- **#54 was never reviewed.** The other session had stopped, probably at its usage limit, and nothing noticed. Two-party review means each side waits on the other, so one stopped session stops the loop.
- **#57 never converged.** It added a rule that the sessions must discuss plans and answer every review point. Each review round found a real flaw in the previous fix:
  - the rule asked for inline threads, which the hook blocks;
  - approval and merge contradicted each other;
  - a question asked in the approving review could be merged unanswered;
  - "every review asks a question" plus "questions block merge" made an endless approve, fix, re-approve cycle.

  Each finding was correct. Taken together, they show that a protocol written in prose is a program without a compiler: every edit opens a new edge case, and the agents are very good at finding them. The fifty-line document spent more review rounds than any product PR.

### 6.4 What worked

- **Reviews with evidence.** On #53, the reviewing session wrote a probe script and showed that a `str` subclass whose `__eq__` always returns true made the validator accept a write to a forbidden field. The author fixed it with exact type checks and answered each finding by number.
- **Honest escalation.** A PR that loosened a control (#52) was labeled `needs-human`, not merged.
- **Agents found gaps in their own setup.** The sessions found the environment-variable problem (#59), the duplicate claim (#55, which led to the "skip issues an open PR already closes" rule), and the protocol contradictions above.
- **The author note** made the agents' work distinguishable on GitHub, which matters because it appears under accounts the maintainers own.

### 6.5 What didn't

- **No liveness.** There was no heartbeat, status page, or alert. When a session hit its usage limit, or `/loop` ended, the other session waited, then stopped too. A maintainer found out by looking. A loop needs a watchdog that reports "no progress in N hours".
- **A long-lived integration branch fights squash-only `main`.**
  - Squash commits on `main` are not ancestors of `agent-main`, so every promotion needs a sync PR with a merge commit back.
  - The commit-message check needed a special case.
  - `Closes #N` closes nothing when a PR merges into `agent-main` rather than the default branch, so #47, #49, #50, and #51 stayed open after their work merged.
- **Claims race.** Picking "the next unassigned issue" without checking for an open PR that already closes it produced duplicate work (#55).
- **Reviewers could not discuss in threads.** Restricting writes to `gh pr review` and `gh pr comment`, for safety, also removed inline review threads. Discussion had to be numbered points in PR bodies.
- **An agent account merged a PR into `main`.** #43 was approved by a maintainer at 18:59 UTC and merged by `mgokcay-agent` at 19:07 UTC. The ruleset was satisfied, because a code owner had approved, so nothing unreviewed reached `main`. This is the residual risk ADR 0010 documents: an agent account with write access can still merge a PR into `main` that a human approved. The history cannot show whether a loop session or a person using the account did it. If a loop session did it, the hook should have refused, since the PR's base was `main`.

## 7. Two maintainers and GitHub's rules

- **"The last push must be approved by someone else" plus two people can deadlock.**
  - If the approver presses *Update branch*, they become the last pusher, and their own approval no longer counts.
  - The author cannot approve their own PR.
  - So only the author may update the branch, which surprised both maintainers on #39 and #43.
- **Required checks with "branch must be up to date"** make parallel PRs merge one at a time, each after an update and a new approval. With agents producing PRs quickly, this was the main source of waiting.
- **Code-owner review covers every path** (`*` in CODEOWNERS), so every PR needed the other maintainer. That was intended for safety-critical paths, but it also applied to typo fixes.

## 8. Incidents

| What | Impact | Lesson |
|---|---|---|
| An agent token pasted visibly into a terminal, stayed in tmux scrollback, and was read by an agent session inspecting the screen | Credential exposure; rotation needed | Enter tokens with `read -s` or a file; clear scrollback; treat scrollback as logged. |
| #43 merged into `main` by an agent account (section [6.5](#65-what-didnt)) | None: a human had approved | An agent account with write access can still merge into `main`. Restrict merges to humans server-side if that matters. |
| #55 duplicated #43 | Wasted work, then a cleanup | Check for open PRs that close an issue before claiming it. |
| The hook blocked commit messages and test files that mentioned `gh pr merge` | Friction | Text-matching guards hit text, not only commands. |
| `make check` failed inside agent sessions because of the session's own environment | False failures, confusion | Controls that read the environment must be tested in an isolated one. |
| The Claude review bot reported a missing section that was present | Misleading review | Bot reviews are advisory and need checking. |
| The loop stopped overnight with no notice | About 12 hours idle | A watchdog is needed. |

## 9. Recommendations for the next project

**Keep:**

1. An ARCHITECTURE.md plus ADRs plus AGENTS.md hierarchy, with hard rules for agents. It is short to write and agents follow it.
2. Component READMEs with numbered, tested invariants.
3. Safety-critical paths as data, with a required `Safety-Impact:` declaration checked in CI.
4. Server-side rulesets as the real boundary, with no bypass actors.
5. Separate reviewing agents (safety, architecture) with a brief to reproduce every claim. They found most real defects.
6. Attribution: `Co-Authored-By`, `AI involvement`, and an author note when agents act under shared or human-owned accounts.

**Change:**

1. **Build a thin vertical slice first.** Get one end-to-end path working (read → agent → proposal → confirm → write) before the template, the eval harness, the orchestrator placeholders, and most of the governance. Cap process work, for example at one process PR per two product PRs.
2. **Put controls on the server, and keep hooks for UX.** If agents must never merge into `main`, give them no write access there, through accounts, a GitHub App, or rulesets limiting who can merge. Do not rely on a shell-text filter.
3. **Give agents machine identities from day one,** preferably a GitHub App, which is not a code owner and whose permissions are visible. Never put agents on maintainers' accounts.
4. **Keep agent protocols mechanical.** Prefer a few rules a CI check can verify (a review exists, a label is set, a required check passes) over pages of prose that two agents must interpret the same way. If a rule can't be checked, expect the agents to find its contradictions.
5. **Treat an agent loop as a service.** Give it a single queue with claims that cannot race, a heartbeat, a "no progress in N hours" alert, and a usage budget per side. If one side may stop, let a human, or a second instance of the same side, take over reviews.
6. **Avoid a long-lived integration branch if possible.** Alternatives: agents open PRs into `main` with an "agent-approved" label and a human merges them in batches, or a merge queue with a required human approval. Either keeps `Closes #N`, history, and promotion simple.
7. **Size the rules to the team.** With two maintainers, code-owner review on every path, last-push approval, and up-to-date branches multiply waiting. Apply the strictest rules to safety-critical paths, not to everything.
8. **Handle secrets as if the terminal is logged,** because with agents watching it, it is.

## 10. Timeline

| Date | Event |
|---|---|
| 2026-09-15 | Repository bootstrapped: architecture, conventions, ruleset, CI |
| 2026-09-16 | ADRs 0003–0005 (Python, Agent Runtime, REST adapter); Claude GitHub app connected; "lobe" renamed to "habit" |
| 2026-09-17–18 | Python workspace and CI; project renamed; six PRs to get the Claude workflow sandbox running |
| 2026-09-19 | Safety Policy loader (#31); ADR 0008 |
| 2026-09-21 | Azure DevOps adapter reads (#35); automatic Claude review (#37) |
| 2026-09-23–24 | Reviews of #39 and #43 against the repository's rules; ADR 0010 designed and reviewed (#46) |
| 2026-09-25 | #46 merged; agent accounts created; the loop starts; #48 and #53 merged by the loop; #39 and #43 merged into `main`; first sync (#58) |
| 2026-09-26 | #52 merged by a maintainer; #57 reaches its fifth review round; the loop stops |
| 2026-10-07 | Project closed; the loop session stopped; this retrospective written |
