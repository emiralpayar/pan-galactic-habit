# Apply tags

## When to use

Use when a work item's Tags don't reflect its affected area, or a relevant tag already in use elsewhere in the project is missing.

## Steps

1. Read the work item's Description, Area Path, and existing Tags.
2. List tags already used elsewhere in the project, from items read in the same session, that plausibly apply.
3. Propose adding tags from that existing set only; do not invent a new tag name.
4. Propose removing a tag only when it directly contradicts the item's current content, for example a tag naming a component the item no longer touches.

## Rules

- Never invent a new tag; if no existing tag fits, propose no tag change and say so.
- Do not use Tags to encode information that belongs in a State or Assignment field — the habit cannot write either field.
- Keep the suggested tag set small; prefer the two or three tags that most specifically describe the item over an exhaustive list.

## Examples

### Good

Item touches the sync job's retry logic; existing project tags include `sync`, `reliability`, `frontend`. Suggested: add `sync`, `reliability`.

### Bad

Item touches the sync job; suggested: add `backend-sync-retry-logic`.

This invents a new tag instead of using `sync`, which is already in use.
