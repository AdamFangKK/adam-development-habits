#!/usr/bin/env python3
"""Create the deterministic V9 preregistration envelope from frozen inputs."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import cast

from analyze_skill_effect_v9 import balanced_condition_order


CODEX_CLI_VERSION = "codex-cli 0.149.0-alpha.4.1"
DEFAULT_CODEX_AUTH_MODE = "chatgpt"
SUPPORTED_CODEX_AUTH_MODES = frozenset({"api-key", "chatgpt"})
CONNECTIVITY_PROBE_TIMEOUT_SECONDS = 60.0
DEFAULT_HARNESS_ID = "codex-cli-0.149.0-alpha.4.1;exec-json;workspace-write;ephemeral;skill-search-disabled;absolute-output;condition-checkpointed-v9"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha256(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_object(path: Path) -> dict[str, object]:
    value = cast(object, json.loads(path.read_text(encoding="utf-8")))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain an object")
    return cast(dict[str, object], value)


def validated_auth_mode(value: str) -> str:
    if value not in SUPPORTED_CODEX_AUTH_MODES:
        raise ValueError(f"unsupported Codex authentication mode: {value}")
    return value


def create(
    *,
    corpus: Path,
    prompts: Path,
    old_skill: Path,
    new_skill: Path,
    runner: Path,
    scorer: Path,
    analyzer: Path,
    auditor: Path,
    generator: Path,
    wrapper: Path,
    output: Path,
    git_commit: str,
    model: str,
    harness: str,
    auth_mode: str = DEFAULT_CODEX_AUTH_MODE,
) -> dict[str, object]:
    auth_mode = validated_auth_mode(auth_mode)
    if output.exists() or output.is_symlink():
        raise FileExistsError(f"refusing to overwrite preregistration: {output}")
    manifest = load_object(corpus / "manifest.json")
    tasks = cast(list[object], manifest.get("tasks"))
    if len(tasks) != 40:
        raise ValueError("V9 preregistration requires 40 corpus tasks")
    random_seed = 20260827
    task_plan = [
        {
            "task_id": cast(dict[str, object], task)["task_id"],
            "cohort": cast(dict[str, object], task)["cohort"],
            "stratum": cast(dict[str, object], task)["stratum"],
            "execution_order": list(balanced_condition_order(random_seed, index)),
        }
        for index, task in enumerate(tasks)
    ]
    decision_ids = [
        str(task["task_id"])
        for task in task_plan
        if task["cohort"] == "decision-retention"
    ]
    protocol = {
        "agent_timeout_seconds": 420.0,
        "test_timeout_seconds": 30.0,
        "connectivity_probe_timeout_seconds": CONNECTIVITY_PROBE_TIMEOUT_SECONDS,
        "pairing": "same task, randomized three-condition order",
        "conditions": ["no_skill", "old_skill", "new_skill"],
        "codex_cli_version": CODEX_CLI_VERSION,
        "codex_auth_mode": auth_mode,
        "skill_search_disabled_for_all_conditions": True,
        "treatment_requires_snapshot_read_evidence": True,
        "hidden_scorer_blind_to_condition": True,
        "corpus_manifest_sha256": sha256(corpus / "manifest.json"),
        "baseline_prompt_sha256": sha256(prompts / "no_skill.txt"),
        "old_skill_prompt_sha256": sha256(prompts / "old_skill.txt"),
        "new_skill_prompt_sha256": sha256(prompts / "new_skill.txt"),
        "old_skill_sha256": sha256(old_skill),
        "new_skill_sha256": sha256(new_skill),
        "runner_sha256": sha256(runner),
        "hidden_scorer_sha256": sha256(scorer),
        "analyzer_sha256": sha256(analyzer),
        "isolation_auditor_sha256": sha256(auditor),
        "generator_sha256": sha256(generator),
        "preregistration_generator_sha256": sha256(Path(__file__).resolve()),
        "artifact_manifest_generator_sha256": sha256(Path(__file__).with_name("generate_effect_artifact_manifest_v9.py")),
        "codex_wrapper_sha256": sha256(wrapper),
    }
    scope = {
        "claim": "For the fixed model, Harness, old/new Skill snapshots, held-out V9 corpus, and blind scorer declared here, enabling the new Skill improves hidden repair success over the old Skill.",
        "model_id": model,
        "harness_id": harness,
        "no_skill_isolation": "automatic Skill discovery disabled; no Skill path supplied",
        "old_skill_revision_sha256": protocol["old_skill_sha256"],
        "new_skill_revision_sha256": protocol["new_skill_sha256"],
    }
    analysis = {
        "alpha": 0.05,
        "bootstrap_resamples": 10000,
        "permutation_resamples": 10000,
        "random_seed": random_seed,
        "minimum_effect": 0.05,
        "minimum_tasks_per_cohort": 20,
        "stratum_weights": {"single-module": 0.2, "cross-module": 0.4, "integration": 0.4},
        "primary_contrast": "new_skill-old_skill",
        "secondary_anchor": "new_skill-no_skill",
        "critical_safety_task_ids": decision_ids,
    }
    task_plan_value = {"tasks": task_plan}
    stopping_rule = {
        "kind": "fixed_complete_blocks",
        "blocks_per_task": 1,
        "early_stop": "not allowed",
        "interrupted_or_excluded_trials": "retain and mark collection ineligible; no selective retry",
    }
    envelope = {
        "scope": scope,
        "protocol": protocol,
        "analysis": analysis,
        "task_plan": task_plan_value,
        "stopping_rule": stopping_rule,
    }
    record: dict[str, object] = {
        "schema_version": 2,
        "experiment_id": "adam-skill-effect-v9",
        "status": "planned",
        "scope": scope,
        "protocol": protocol,
        "analysis": analysis,
        "task_plan": task_plan_value,
        "stopping_rule": stopping_rule,
        "preregistration": {
            "git_commit": git_commit,
            "envelope_sha256": canonical_sha256(envelope),
            "recorded_before_first_trial": True,
            "raw_artifacts_append_only": True,
            "references_unavailable_to_agents": True,
        },
        "trials": [],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    _ = output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ("corpus", "prompts", "old-skill", "new-skill", "runner", "scorer", "analyzer", "auditor", "generator", "wrapper", "output"):
        _ = parser.add_argument(f"--{option}", type=Path, required=True)
    _ = parser.add_argument("--git-commit", required=True)
    _ = parser.add_argument("--model", default="gpt-5.6-terra")
    _ = parser.add_argument("--harness", default=DEFAULT_HARNESS_ID)
    _ = parser.add_argument("--auth-mode", choices=sorted(SUPPORTED_CODEX_AUTH_MODES), default=DEFAULT_CODEX_AUTH_MODE)
    arguments = parser.parse_args()
    _ = create(**vars(arguments))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
