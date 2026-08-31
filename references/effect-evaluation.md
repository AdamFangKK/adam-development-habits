# Skill Effect Evaluation

Use this protocol only for a claim that enabling the Skill improves repair success or causal-analysis quality. It measures a fixed model and Harness on a declared corpus; it cannot prove a general property of a model or deployment.

## Pre-register Before Any Run

Create one JSON experiment record from `examples/skill-effect-preregistration.json` before collecting results. Fill its task IDs/strata and fixed stopping rule, commit it, then record the immutable commit SHA in the completed record. Freeze the corpus manifest, public task prompt, baseline prompt, Skill prompt, hidden scorer, Skill revision, analysis seed, practical threshold, sample target, strata, randomized condition order, and stopping rule in the envelope digest. Run formal collection from a clean Git worktree at that commit; keep all declared inputs within it, reject symbolic links, and verify their bytes immediately before execution. The baseline and treatment must differ only by the presence of the Skill and its necessary invocation instruction.

Also freeze the non-secret Codex CLI version and authentication mode. Verify the mode with `codex login status` before collection, but never store, print, or hash a credential or access token in the preregistration or evidence artifacts.

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

For multi-file causal-repair tasks, use the v6 workspace protocol when the current function-level runner cannot express the responsible owner. The public task workspace contains only implementation files, task metadata, and public tests. The runner records the exact allowed edit paths, runs the public command after the Agent exits, and injects the scorer-only hidden test tree into a temporary copy after that exit. Hidden scoring must execute the public and hidden suite together, reject any path outside the registered implementation set, and never copy hidden files back into Agent artifacts. The v6 runner writes an atomic checkpoint after every complete pair; a process or service interruption is an ineligible interrupted collection, not a partial result to be analyzed or selectively retried.

## V9 Three-Condition Protocol

V8 is retained only as historical protocol evidence and must not be cited as capability evidence. Its hidden layout could contain reference implementation files, and its scorer copied the entire hidden tree over the candidate before running tests. A hidden pass from that protocol therefore cannot prove that an Agent repaired the candidate.

Use V9 for new effect claims. It compares `no_skill`, a frozen old Skill, and a frozen new Skill on the same task. The primary contrast is `new_skill - old_skill`; `new_skill - no_skill` is a secondary anchor. Analyze the decision-retention and end-to-end repair cohorts separately. Both preregistered cohorts must pass the practical-effect, confidence-interval, randomization, isolation, and critical-safety gates before reporting improvement.

The V9 corpus uses separate roots:

- `tasks/<task-id>` contains only the Agent-visible buggy workspace and public tests.
- `hidden-tests/<task-id>` contains only tests injected after Agent exit.
- `references/<task-id>` contains the fixed implementation for corpus validation only and is never an Agent or scorer input.

The V9 scorer accepts no reference path, rejects symbolic links and path collisions, injects tests only, and verifies every allowed implementation file has the same SHA-256 before and after injection. Retain every non-secret prompt, absolute Agent output, stdout, stderr, diff, public result, hidden result, audit, collection result, analysis, and artifact hash manifest. Existing output paths are an error; interrupted or excluded trials remain in the record and make the collection ineligible rather than eligible for selective retry.

For the automatic-retirement capability, materialize the dedicated cleanup profile with:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/materialize_effect_corpus_v9.py \
  --profile cleanup --corpus examples/effect-corpus-v9-cleanup
```

This held-out split has 40 tasks (20 `decision-retention`, 20 `repair`) across the same `6/8/6` strata. Repair tasks contain obsolete implementations; decision-retention tasks deliberately let the public suite pass while hidden tests check duplicate removal, legitimate dynamic retention, and synchronized current documentation. Each cleanup task now includes implementation plus README/docs and, by kind, a legacy file, duplicate helper, dynamic adapter/registry, or stale configuration surface. The manifest lists those non-test paths as the only editable scope, and the hidden tree contains tests only; the reference tree is validation-only. All three conditions share the same task framing, editable scope, deletion rule, test command, and isolation limits; only the no-Skill versus frozen old/new Skill availability and content may differ. Run `tests/test_cleanup_effect_corpus.py` before preregistering; do not use its reference sources or hidden tests as Agent inputs.

Generate the cleanup-specific envelope at `examples/effect-experiment-v9/cleanup-preregistration-v13.json` with `create_effect_preregistration_v9.py` after the cleanup corpus and old/new `SKILL.md` snapshots are committed. The preregistration is intentionally `planned`; `analyze_skill_effect_v9.py` must report `not_run`/`unknown` until all fixed-order three-condition pairs complete. Keep a superseded, unrun envelope byte-for-byte intact rather than changing its input hashes after the fact.

When a trial emits process or runtime checkpoint JSONL, validate it with `scripts/validate_development_events.py`. The checker enforces the Level 0/1/2 event threshold, stable bounded names, unique logical transitions, lifecycle coverage, and sensitive-field rejection. Event validity is a telemetry-quality gate and never substitutes for the hidden behavioral contract.
