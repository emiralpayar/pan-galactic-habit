## Summary

<!-- What does this PR change, and why? Keep it to one concern. -->

## Linked issue

Closes #

## Type of change

- [ ] Memory (`habits/*/memory/`)
- [ ] Behavior (agent, orchestrator, improver, or interface code)
- [ ] Safety-critical (see CONTRIBUTING.md#safety-critical-changes)
- [ ] Documentation, tooling, or CI

## Safety impact

<!--
Required. Set the value on the line below to one of:
  none      no safety-critical paths touched
  neutral   touches safety-critical files without changing what is allowed
  tightens  something previously allowed no longer is
  loosens   something previously disallowed now is — explain what and why below
The Safety guard check fails if safety-critical paths change and the value is "none".
-->

Safety-Impact: none

## How was this verified?

<!-- Commands run, evals added or updated, manual checks performed. -->

- [ ] `make check` passes locally

## AI involvement

<!-- none | assisted (a human drove an AI coding session) | authored (autonomous agent) -->

## Author checklist

- [ ] The PR title is a valid Conventional Commit header (it becomes the squash commit message)
- [ ] I reviewed my own diff before requesting review
- [ ] Tests or evals cover the change (or I explained why they can't)
- [ ] ARCHITECTURE.md, component READMEs, and ADRs are updated if affected
- [ ] No secrets, tokens, or real customer data — including in fixtures and examples
