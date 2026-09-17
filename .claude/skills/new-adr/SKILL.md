---
name: new-adr
description: Record an architecture decision as a numbered ADR in docs/adr. Use when a change makes a hard-to-reverse decision, resolves an open question from ARCHITECTURE.md §11, or chooses between reasonable alternatives.
---

# New ADR

## Steps

1. **Confirm an ADR is warranted.** See `docs/adr/README.md` for when to write one. Small, easily reversed choices don't need one.
2. **Gather the facts** before writing: the problem, constraints, the options genuinely considered, and who made the decision. If the decision is already made and this PR carries it out — the common case — write the ADR with status `Accepted` directly. Only use `Proposed` if the user has not decided yet and this PR is opening the options for discussion; in that case present the options and do not decide on their behalf.
3. **Create the file:** `scripts/new-adr.sh "<short decision title>"`.
4. **Fill in every section** of the generated file. Keep it short: an ADR is read in two minutes.
   - *Context*: forces at play, stated neutrally.
   - *Decision*: active voice — "We will …".
   - *Consequences*: both the good and the bad.
   - *Alternatives considered*: each with the reason it was not chosen.
5. **Add it to the index** in `docs/adr/README.md`, with the same status.
6. **Update ARCHITECTURE.md** in the same PR if the decision changes it (e.g. move an item from §11 Open Questions to §10 Resolved Design Decisions and link the ADR).
7. **If it supersedes an earlier ADR**, set the old one's status to `Superseded by NNNN` — this is the only edit allowed to an accepted ADR.
8. Commit as `docs: add adr NNNN <topic>` and open a PR with the `open-pr` skill.
