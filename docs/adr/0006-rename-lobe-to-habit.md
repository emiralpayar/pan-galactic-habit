# 0006. Rename "lobe" to "habit"

- **Status:** Proposed
- **Date:** 2026-09-16
- **Deciders:** @mertdonmez98

## Context

ARCHITECTURE.md §1 introduces "lobe" by analogy: *"a lobe is a region of a brain with its own specialized function."* A brain lobe is a physical, anatomical structure — hardware. But what the system actually builds for each lobe is not hardware: it is a specialized, self-contained unit of software behavior (an agent definition, memory, a safety policy, and evals) that the Orchestrator creates on demand and that is versioned in git.

The term therefore points at the wrong half of the brain/mind distinction. It reads naturally in the system's own definition ("a self-contained unit of behavior and memory with one purpose"), but that definition describes a *learned, encoded behavior pattern*, not a *region of tissue*. New contributors reading "lobe" and the accompanying brain-anatomy framing can reasonably conclude the term refers to something structural or hardware-like, which it never was.

The term appears extensively throughout the repository — in ARCHITECTURE.md, AGENTS.md, CLAUDE.md, CONTRIBUTING.md, component READMEs, the `lobes/` directory, the `new-lobe` Claude Code skill, the `lobe_request` issue template, safety-critical path lists, and branch/commit scope conventions — so this is a decision that affects every component and is expensive to reverse once contributors, issues, and history reference the new name.

## Decision

We will rename "lobe" to **"habit"** everywhere in the repository going forward: prose, directory and file names, Claude Code skills, issue templates, safety-critical path lists, branch/commit conventions, and (in a follow-up step after this PR merges) GitHub labels.

"Habit" is the accurate counterpart to "lobe" in the brain/mind analogy: a specialized behavior pattern learned through repetition and encoded in neural pathways (habit formation), not a physical structure — matching what the system actually creates and versions.

Already-accepted ADRs (0001–0005) are not edited by this decision. ADRs are immutable once accepted (docs/adr/README.md); they remain a historical record of the terminology in effect when each was written.

## Consequences

- Terminology now matches the concept: a habit is a learned, software-encoded behavior pattern, not implied hardware.
- One-time cost: every file, directory, skill, template, and convention that mentions "lobe" changes in a single, mechanical, low-risk PR.
- `docs/adr/0001`–`0005` retain the word "lobe" in their body text as a historical record; readers of those ADRs will see the old term. This is expected and intentional, not an inconsistency to fix.
- GitHub labels (`lobe-request`, `agent:lobe`, the `memory` label's description) are live, shared repository state outside git review; they are renamed in a separate, explicitly confirmed step after this PR merges, run via `scripts/bootstrap-github.sh`.
- Future contributors introducing a second self-contained software concept must pick a different word than "habit" or "lobe" for anything else brain/mind-themed, to avoid re-creating this ambiguity.

## Alternatives considered

- **Capsule.** Self-contained, portable software package — no hardware connotation intended, but "capsule" is itself a real anatomical brain structure (the internal/external capsule, white-matter tracts), so it reintroduces the exact problem being fixed.
- **Faculty.** In English, a "mental faculty" is the precise non-physical counterpart to a brain lobe. Rejected because in Turkish (the team's working language) "faculty" reads as "fakülte" (a university faculty), which is a misleading false-friend for a non-English-native team.
- **Specialist.** Reads naturally in prose and emphasizes single-purpose behavior, but it is a very common general English word, which weakens grep/search precision as the codebase grows.
- **Module.** Standard software term, and "modularity of mind" is a real cognitive-science concept (Fodor) for a functional, non-anatomical unit of mind — a strong conceptual fit. Set aside in favor of a biological/process-oriented term once the team leaned toward keeping a brain/mind theme; remains a reasonable fallback if "habit" turns out not to stick.
- **Engram.** The neuroscience term for a memory/skill trace encoded in neurons — a very precise conceptual fit (behavior + memory, not a physical structure) and unclaimed elsewhere in the codebase. Rejected only because the team found the word itself hard to internalize in daily use, despite liking its meaning.
- **Trace / Imprint / Signature.** Considered as more familiar synonyms for "engram." "Trace" risks colliding with software tracing/observability terminology once that exists. "Imprint" and "Signature" were both viable; "habit" was preferred as the more precise fit once "habit formation" (a learned, encoded, repeated behavior pattern) was identified as the closest biological analogy to what a lobe/habit actually is.
- **Instinct / Reflex.** Biological, process-oriented, non-anatomical. Rejected because both imply innate or automatic behavior, which conflicts with a habit being created on demand and deliberately versioned, reviewed, and improved through PRs.
