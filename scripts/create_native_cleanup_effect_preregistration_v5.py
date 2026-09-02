#!/usr/bin/env python3
"""Create a hash-bound V5 plan before native cleanup-effect collection."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, cast

from materialize_native_cleanup_effect_v5 import CONDITIONS, TASKS


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = Path("examples/effect-experiment-native-v5")
ORDER_CYCLE = (
    ("old_skill", "new_skill", "no_skill"),
    ("no_skill", "old_skill", "new_skill"),
    ("new_skill", "no_skill", "old_skill"),
    ("old_skill", "no_skill", "new_skill"),
    ("new_skill", "old_skill", "no_skill"),
    ("no_skill", "new_skill", "old_skill"),
)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha256(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def relative_file_hash(root: Path, relative: Path) -> str:
    path = root / relative
    if not path.is_file():
        raise FileNotFoundError(f"required frozen input is missing: {relative}")
    return file_sha256(path)


def require_manifest_tasks(root: Path) -> list[dict[str, object]]:
    path = root / EXPERIMENT / "manifest.json"
    value = cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))
    tasks = value.get("tasks")
    if not isinstance(tasks, list):
        raise ValueError("V5 manifest must contain a task list")
    expected = [(task.task_id, task.cohort, task.stratum) for task in TASKS]
    observed: list[tuple[str, str, str]] = []
    for raw in tasks:
        if not isinstance(raw, dict):
            raise ValueError("V5 manifest tasks must be objects")
        task_id, cohort, stratum = raw.get("task_id"), raw.get("cohort"), raw.get("stratum")
        if not all(isinstance(item, str) for item in (task_id, cohort, stratum)):
            raise ValueError("V5 manifest task is missing task_id, cohort, or stratum")
        observed.append((cast(str, task_id), cast(str, cohort), cast(str, stratum)))
    if observed != expected:
        raise ValueError("V5 manifest task plan differs from the frozen generator task order")
    return cast(list[dict[str, object]], tasks)


def immutable_envelope(record: dict[str, object]) -> dict[str, object]:
    return {key: record[key] for key in ("scope", "protocol", "analysis", "task_plan", "stopping_rule")}


def create(root: Path = ROOT) -> dict[str, object]:
    root = root.resolve()
    manifest_tasks = require_manifest_tasks(root)
    paths = {
        "corpus_manifest": EXPERIMENT / "manifest.json",
        "generator": Path("scripts/materialize_native_cleanup_effect_v5.py"),
        "runner": Path("scripts/native_cleanup_effect_runner_v5.py"),
        "base_runner": Path("scripts/native_cleanup_effect_runner_v1.py"),
        "analyzer": Path("scripts/analyze_native_cleanup_effect_v5.py"),
        "preregistration_generator": Path("scripts/create_native_cleanup_effect_preregistration_v5.py"),
        "task_prompt": EXPERIMENT / "agent-task-template.txt",
        "old_skill": EXPERIMENT / "skills/old/frozen-policy.md",
        "new_skill": EXPERIMENT / "skills/new/frozen-policy.md",
    }
    hashes = {name: relative_file_hash(root, path) for name, path in paths.items()}
    task_plan = [
        {
            "task_id": task["task_id"],
            "cohort": task["cohort"],
            "stratum": task["stratum"],
            "execution_order": list(ORDER_CYCLE[index % len(ORDER_CYCLE)]),
        }
        for index, task in enumerate(manifest_tasks)
    ]
    protocol = {
        "conditions": list(CONDITIONS),
        "pairing": "same task, preregistered three-condition order with predecessor blind-score SHA-256 chain",
        "agent_timeout_seconds": 300,
        "test_timeout_seconds": 20,
        "corpus_manifest_path": paths["corpus_manifest"].as_posix(),
        "corpus_manifest_sha256": hashes["corpus_manifest"],
        "generator_path": paths["generator"].as_posix(),
        "generator_sha256": hashes["generator"],
        "runner_path": paths["runner"].as_posix(),
        "runner_sha256": hashes["runner"],
        "base_runner_path": paths["base_runner"].as_posix(),
        "base_runner_sha256": hashes["base_runner"],
        "analyzer_path": paths["analyzer"].as_posix(),
        "analyzer_sha256": hashes["analyzer"],
        "preregistration_generator_path": paths["preregistration_generator"].as_posix(),
        "preregistration_generator_sha256": hashes["preregistration_generator"],
        "task_prompt_path": paths["task_prompt"].as_posix(),
        "task_prompt_sha256": hashes["task_prompt"],
        "old_skill_path": paths["old_skill"].as_posix(),
        "old_skill_sha256": hashes["old_skill"],
        "new_skill_path": paths["new_skill"].as_posix(),
        "new_skill_sha256": hashes["new_skill"],
        "hidden_scorer": "the hash-bound native_cleanup_effect_runner_v1 base scorer copies only tests/test_hidden.py from the private V5 corpus into a disposable scoring candidate after the native subagent returns",
        "hidden_scorer_blind_to_condition": True,
        "sequence_enforcement": "native_cleanup_effect_runner_v5 permits a later condition only after a predecessor has an agent-exit record and a scored_after_agent_exit credential; a failed hidden or implementation-integrity check remains a retained failed sample rather than a sequence blocker, and the V5 analyzer verifies the chain",
        "agent_provenance": "each completed condition records the native agent identity, fixed model identifier, ordered UTC timestamps, frozen prompt hash, condition-input and workspace-handoff fingerprints, and a transcript hash; the analyzer requires all fields and replays the candidate diff independently",
        "allowed_agent_input": ["task workspace", "condition-specific frozen Skill snapshot when supplied"],
        "agent_must_not_receive": ["hidden tests", "reference tree", "scoring rubric", "prior trial outputs", "condition outcome"],
    }
    record: dict[str, object] = {
        "schema_version": 2,
        "experiment_id": "adam-native-cleanup-effect-v5",
        "status": "planned",
        "scope": {
            "claim": "For the fixed native Codex subagent model, shared-filesystem Harness, frozen old/new Skill snapshots, selected unused V10-derived V5 corpus, and blind hidden scorer declared here, enabling the new Skill improves automatic retirement and documentation-synchronization success over the old Skill.",
            "model_id": "gpt-5.5",
            "harness_id": "codex-app-native-subagent;shared-filesystem;protocol-isolated;task-workspace-only;predecessor-score-chain;manual-hidden-scorer-v5",
            "old_skill_revision_sha256": hashes["old_skill"],
            "new_skill_revision_sha256": hashes["new_skill"],
            "isolation_limit": "Native subagents share a filesystem and are instructed to read only the supplied workspace and condition policy. The parent Harness is trusted to record the actual native-agent identity and transcript; this is protocol isolation and audit provenance, not container isolation or cryptographic agent attestation.",
        },
        "protocol": protocol,
        "analysis": {
            "alpha": 0.05,
            "minimum_effect": 0.2,
            "primary_contrast": "new_skill-old_skill",
            "secondary_anchor": "new_skill-no_skill",
            "test": "exact one-sided paired sign-flip test over non-tied task-level hidden-contract outcomes",
            "critical_safety_cohort": "decision-retention",
            "claim_rule": "eligible collection, primary effect at least minimum_effect, primary p-value at most alpha, no new-skill regression against old_skill in decision-retention, and non-negative secondary effect",
        },
        "task_plan": {"tasks": task_plan},
        "stopping_rule": {
            "kind": "fixed_complete_blocks",
            "blocks_per_task": 1,
            "early_stop": "not allowed",
            "interrupted_or_excluded_trials": "retain and mark collection ineligible; no selective retry",
        },
        "preregistration": {
            "recorded_before_first_trial": True,
            "raw_artifacts_append_only": True,
            "references_unavailable_to_agents": True,
        },
        "trials": [],
    }
    preregistration = cast(dict[str, object], record["preregistration"])
    preregistration["protocol_sha256"] = canonical_sha256(protocol)
    preregistration["envelope_sha256"] = canonical_sha256(immutable_envelope(record))
    return record


def write_preregistration(output: Path, *, root: Path = ROOT) -> dict[str, object]:
    if output.exists():
        raise FileExistsError(f"refusing to overwrite preregistration: {output}")
    record = create(root)
    output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    _ = parser.add_argument("--output", type=Path, required=True)
    _ = parser.add_argument("--root", type=Path, default=ROOT)
    arguments = parser.parse_args()
    print(json.dumps(write_preregistration(arguments.output, root=arguments.root), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
