---
name: new-habit
description: Scaffold a new habit (agent, memory, safety policy, evals) following the template in ARCHITECTURE.md §5. Use when asked to create a new habit or agentic flow in this repository.
---

# New habit

A habit is only as safe as its Safety Policy and only as reviewable as its evals. Do not skip either.

## Before scaffolding

1. **Get the requirements.** Ideally from a `habit-request` issue. You need: name, purpose, external system, what it reads, exactly what it may write, what it must never do, write budgets, and example inputs with expected outcomes. Ask for anything missing — do not invent write permissions.
2. **Check what exists:** `ls habits/ adapters/`. Reuse the Chat Interface, the Safety Layer engine, and an existing adapter where possible (ARCHITECTURE.md §5.1).
3. **Check the phase.** Until the habit template is extracted (ARCHITECTURE.md §12, step 2), the implementation language and structure are defined by `habits/backlog-refiner/`. If that habit is not implemented yet, tell the user that scaffolding can only produce the folder structure, memory, policy draft, and eval cases.

## Scaffold

Create the structure described in `habits/README.md`:

```text
habits/<name>/
  README.md               # purpose, external system, reads, writes, status
  agent/                  # agent definition and flow code
  memory/
    instructions.md       # follows docs/development/memory-style-guide.md
    skills/
  policy/
    safety-policy.yaml    # field allowlist, forbidden operations, budgets
  evals/
    fixtures/             # synthetic inputs only
    cases/                # expected qualities per fixture
```

## Rules

- The name is lowercase kebab-case; it automatically becomes a valid commit scope.
- The Safety Policy is **deny by default**: list only what is explicitly allowed.
- Budgets must be set at all three levels (per call, per session, per time window).
- Eval fixtures are synthetic. Never copy real work items or customer data.
- Never give the agent raw access to the external system's write tools.
- A new habit is safety-critical (it adds a policy): run the `safety-reviewer` subagent, then open the PR with the `open-pr` skill using `Safety-Impact: loosens` and an explanation of the new write capabilities.
- If the habit needs a new adapter, that is a separate PR that lands first.
