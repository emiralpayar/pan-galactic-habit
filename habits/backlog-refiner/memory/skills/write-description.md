# Write description

## When to use

The work item's Description is empty, is a single vague sentence, or does not let a reader tell what problem it addresses or what outcome is wanted.

## Steps

1. Read the title, the existing Description, and any comments or linked wiki pages the user has pointed you to.
2. Write a **Problem** paragraph: what is wrong or missing today, and who is affected. Use only what the title, existing text, or user-supplied context state.
3. Write a **Outcome** paragraph: what should be true once the item is done.
4. If the existing text names a constraint, a non-goal, or a specific approach, keep it; do not add one that was not already present.
5. Compose the full replacement Description from these parts and propose it as one field value.

## Rules

- Do not shorten or drop information already present in the original Description; refine its wording, don't summarize it away.
- Do not propose an approach or implementation detail that was not in the original text or in what the user told you — that belongs in Acceptance Criteria or a separate conversation, not invented here.
- If the title and existing text together do not state a problem or an outcome, do not guess one: report that the item needs more input instead of proposing a Description.

## Examples

### Good

Original: "fix the login thing"

Proposed:

> **Problem:** Users report the login form accepts a blank password and signs them in as a guest instead of showing a validation error.
>
> **Outcome:** Submitting the login form with a blank password shows a validation error and does not sign the user in.

This states the problem and the outcome using only what the (synthetic) original text and title implied, without inventing a root cause or a fix.

### Bad

Original: "fix the login thing"

Proposed:

> **Problem:** The password hashing library is outdated and vulnerable to timing attacks.
>
> **Outcome:** Replace bcrypt with argon2 across the auth service.

This invents a root cause and a specific technical fix that were not in the original item — a Description should state the problem and outcome, not a guessed implementation the author never asked for.
