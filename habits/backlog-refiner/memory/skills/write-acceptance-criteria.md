# Write acceptance criteria

## When to use

The work item's Acceptance Criteria is empty, or does not let someone tell, without asking the author, whether the item is done.

## Steps

1. Read the Description (proposing a Description first if it also needs one) and any comments or wiki pages the user pointed you to.
2. List each distinct outcome the Description implies.
3. Write one Given/When/Then statement per outcome: the starting state, the action, and the observable result.
4. Order statements from the primary behavior to edge cases.
5. Compose the full replacement Acceptance Criteria from these statements and propose it as one field value.

## Rules

- Write each statement as Given/When/Then, one statement per line.
- Each statement must describe something observable (a visible result, a returned value, a state change) — never an internal implementation step.
- Do not add a statement for behavior the Description does not imply; propose a Description change first if the scope is unclear.
- Keep statements independently verifiable: someone should be able to check one without depending on another passing first.

## Examples

### Good

Description problem/outcome: "Submitting the login form with a blank password shows a validation error and does not sign the user in."

Proposed Acceptance Criteria:

> - Given the login form, when the user submits it with a blank password, then a validation error is shown.
> - Given the login form, when the user submits it with a blank password, then no session is created and the user stays on the login page.

Each line is observable and checkable on its own.

### Bad

Proposed Acceptance Criteria:

> - Add a check in the auth controller before calling the session service.
> - Make sure the code is clean and well tested.

The first line describes an implementation step, not an observable outcome; the second is not checkable by anyone without further interpretation.
