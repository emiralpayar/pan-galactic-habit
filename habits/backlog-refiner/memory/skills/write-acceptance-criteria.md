# Write acceptance criteria

## When to use

Use when a work item has no Acceptance Criteria, or has criteria that are not independently testable.

## Steps

1. Read the work item's Description and any comments describing what "done" looks like.
2. Write each criterion as a Given/When/Then statement: the starting state, the triggering action, the expected outcome.
3. Cover the happy path first.
4. Add an edge case only when the Description or comments make it evident; do not invent edge cases from nothing.
5. Keep each criterion independent — a reader must be able to verify it without another criterion being true first, where the content allows it.

## Rules

- Each criterion states one outcome; split a criterion that contains "and" into two.
- Every criterion must be checkable by someone who did not write it, from the item's content alone.
- Do not restate the Description as a criterion; a criterion describes an outcome, not the task.
- Only propose text for the Acceptance Criteria field — this skill does not cover Description or Tags.

## Examples

### Good

Given a user with items in their cart, when they select "checkout" with an expired payment method, then the checkout is blocked and an error names the payment method as the reason.

### Bad

"Checkout should work correctly for all payment scenarios."

This isn't independently testable: it states no starting state, no trigger, and no observable outcome.
