# Skill Effect Evaluation

Use this protocol only for a claim that enabling the Skill improves repair success or causal-analysis quality. It measures a fixed model and Harness on a declared corpus; it cannot prove a general property of a model or deployment.

## Pre-register Before Any Run

Create one JSON experiment record from `examples/skill-effect-preregistration.json` before collecting results. Fill its task IDs/strata and fixed stopping rule, commit it, then record the immutable commit SHA in the completed record. Freeze the corpus manifest, public task prompt, baseline prompt, Skill prompt, hidden scorer, Skill revision, analysis seed, practical threshold, sample target, strata, randomized condition order, and stopping rule in the envelope digest. The baseline and treatment must differ only by the presence of the Skill and its necessary invocation instruction.

Use a held-out corpus. Keep references, hidden tests, expected patches, scoring rubrics, and prior candidate outputs unavailable to repair agents. Give a blind scorer candidate diffs and test outcomes without condition labels. Run both conditions for every task, randomize their order within each pair, retain raw outputs/diffs/logs, and record every exclusion before looking at results.

## Measure and Decide

Use hidden repair success as the primary binary metric. Optionally add a preregistered, blind causal-quality score in `[0, 1]`, but never replace the hidden repair contract with a prose rubric. Cluster repeated runs by task: multiple attempts on one task are not independent samples. The completed record must contain every planned task and exactly the declared number of pairs for each task; an interrupted or excluded run is not silently dropped.

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/analyze_skill_effect.py \
  examples/skill-effect-preregistration.json
```

The analyzer performs a stratified task-cluster bootstrap and a paired sign-flip randomization test. It reports `improved` only when the experiment has at least the preregistered number of distinct tasks, the one-sided paired randomization result is below `alpha`, and the lower 95% confidence bound exceeds the preregistered practical threshold. `inconclusive` means more or better-isolated data are needed; `no_demonstrated_improvement` means the upper bound is non-positive. `--require-improvement` is suitable for a declared gate, not exploratory tuning.

## Interpretation and Iteration

An `improved` result supports only this statement: “On the preregistered corpus, fixed model, fixed Harness, and hidden scorer, enabling this version of the Skill improved the named metric.” It does not establish model-wide reasoning, production safety, or a causal effect independent of the Harness.

When a result is inconclusive, preserve all attempts and label failures before changing the Skill: missed owner, untested alternative, shallow-public-test repair, hidden-contract failure, unsafe side effect, unnecessary scope, or tool/authority violation. Change the smallest Skill rule that addresses a recurring category, pre-register a new version, and rerun on a new held-out corpus. Do not tune the Skill against the same hidden set and then report it as a fresh result.

Native Codex subagents sharing a filesystem provide only protocol isolation. A stronger effect claim requires separate worktrees or containers, independent prompt/output storage, deterministic environment capture, and a scorer that cannot read condition labels.
