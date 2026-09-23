# Write descriptions

## When to use

Use when a work item's Description is missing, too short to convey the problem, or written as a solution without stating the underlying need.

## Steps

1. Read the work item's title, existing Description, comments, and any linked wiki page content.
2. Identify the problem or user need the item addresses, distinct from any specific implementation it suggests.
3. Draft a Description with the problem statement first, followed by the original's proposed solution or approach, if it had one.
4. Keep the author's own words and decisions; rewrite for clarity, not for scope.
5. If the problem can't be inferred from the available content, propose no change and say what's missing instead.

## Rules

- State the problem before the solution.
- Do not add a solution to an item that only stated the problem.
- Do not invent details that are not present in the title, existing description, comments, or wiki page.
- Keep the description short enough to render fully in a work item's summary view — aim for under 500 words.

## Examples

### Good

Original: "Add retry to the sync job"

Suggested: "The nightly sync job fails permanently on a single transient network error, losing a day of data. Add retry with backoff so a transient failure doesn't require a manual rerun."

### Bad

Original: "Add retry to the sync job"

Suggested: "Add exponential backoff retry with a maximum of 5 attempts and a 30 second cap, implemented in `sync/client.py`."

This invents an implementation the author never specified, instead of stating the problem the original title implies.
