# Audit-driven optimization acceptance

Scope: Level 2 changes to the existing optional planner and active Skill policy,
README, corresponding regression tests, and this change's evidence. No new
dependencies, production operations, or GitHub push.

Canonical owners: `scripts/plan_capability_composition.py:plan` for previews;
`SKILL.md` for the development policy. Observed failures: refactor prerequisites
were not activated, existing output labels made mandatory gates falsely block,
Level 0 activated retirement, and malformed required facts disappeared. Active
policy also required magic owner comments and conflicted over historical text
and read-only causal diagnosis.

Acceptance:

- A refactor/remote-write preview can obtain missing owner prerequisites without
  fabricating observed evidence; mandatory gates cannot be bypassed.
- Valid evidence reuse and stale evidence handling are explicit. Planning facts
  remain separate from actual execution and verified facts.
- Level 0 does no capability work, contradictory levels and malformed inputs fail.
- Accurate history is preserved, stale current guidance is synchronized, ownership
  comes from implementation/callers/contracts/tests rather than magic comments.
- Causal diagnosis is separate from applied/verified repair; no unrun repair claim.
- Simple work uses a small shared record, conditional controls remain required.
- Existing package checks plus new counterexamples and an independent fresh-context
  forward task pass. Structural assertions alone do not establish model uplift.

Forward fixture: `/tmp/adam-forward-JBVNpm`, raw account normalization request,
existing canonical implementation, CLI plus JSON-loaded adapter, stale current
guidance and accurate historical release text. Baseline public tests: 2 failures.
The evaluating agent receives the raw request/workspace and current Skill, not
the acceptance rubric or this plan. The parent will inspect actual artifacts and
run held-out input/dispatch checks after the agent returns. This is protocol
isolation on a shared machine, not a security sandbox or statistical effect study.

Rollback: revert this logical change together. Preserve existing archived
experiments and evidence; no historical artifact is rewritten to fit new policy.
