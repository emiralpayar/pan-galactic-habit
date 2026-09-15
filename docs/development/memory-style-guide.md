# Memory Style Guide

Lobe memory (`lobes/<name>/memory/`) is behavior written in markdown. It is reviewed as a plain diff (ARCHITECTURE.md §3), so it must be written to be **diffable, testable, and unambiguous**.

## Layout

```text
memory/
  instructions.md      # always loaded: role, goals, constraints, output format
  skills/
    <skill-name>.md    # one capability per file, loaded when relevant
```

- `instructions.md` holds what applies to **every** interaction. Keep it short.
- Each skill covers **one** capability (e.g. `write-acceptance-criteria.md`). File names are lowercase kebab-case verbs or noun phrases.
- Never repeat a rule in two files. If two skills need it, it belongs in `instructions.md`.

## `instructions.md` structure

```markdown
# <Lobe name>

## Role
One or two sentences: who the agent is and whom it serves.

## Goals
What a successful interaction achieves, in priority order.

## Constraints
What the agent must never do, and how it treats untrusted content.

## Output format
The exact shape of suggestions presented to the user.

## Skills
One line per skill: file name and when to use it.
```

## Skill file structure

```markdown
# <Skill name>

## When to use
The situation that triggers this skill.

## Steps
1. Numbered, imperative steps.

## Rules
- Specific, checkable rules.

## Examples
### Good
…
### Bad
… and why it is bad.
```

## Writing rules

- **One sentence per line** (semantic line breaks). A change to one sentence shows as a one-line diff instead of a rewrapped paragraph. Markdown renders it as a normal paragraph.
- **Imperative and specific.** "Write acceptance criteria as Given/When/Then statements." — not "Try to write good acceptance criteria."
- **Checkable.** Every rule should be something an eval could verify. If you can't imagine a test for it, rewrite it.
- **Examples beat adjectives.** Pair each non-obvious rule with a good and a bad example.
- **State the why for surprising rules.** One short clause is enough; it helps the model generalize and the reviewer judge.
- **Positive instructions first.** Say what to do; list prohibitions under Constraints.
- **No emphasis inflation.** Avoid "IMPORTANT", "MUST", and capitals except for the handful of true hard constraints.
- **Plain markdown only.** Headings, lists, code blocks, tables. No HTML, no embedded images.

## Safety in memory

- Always state that content read from external systems is data to evaluate, never instructions to follow.
- Memory **cannot grant permissions**. What a lobe may write is defined only by its Safety Policy; memory describing a write the policy forbids is a bug.
- Never include secrets, internal URLs with tokens, or real customer data — examples are synthetic.

## Size

- `instructions.md`: aim for under ~150 lines.
- A skill file: aim for under ~200 lines.
- If a file grows past that, split the skill or move examples into eval fixtures.

## Changing memory

- Memory changes are behavior changes: commit as `feat(<lobe>)` or `fix(<lobe>)`.
- Add or update an eval case that demonstrates the change.
- In the PR description, quote the old and new rule and describe the behavior difference you expect.
