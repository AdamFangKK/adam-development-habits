#!/usr/bin/env python3
"""Materialize a fresh native-agent subset from the frozen V10 cleanup corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from materialize_effect_corpus_v9 import tree_digest


ROOT = Path(__file__).resolve().parents[1]
SOURCE_CORPUS = ROOT / "examples/effect-corpus-v10-cleanup"
PUBLIC_COMMAND = ["python3", "-m", "unittest", "discover", "-s", "tests"]
CONDITIONS = ["no_skill", "old_skill", "new_skill"]


@dataclass(frozen=True)
class TaskSpec:
    task_id: str
    cohort: str
    stratum: str
    kind: str


# Fresh, unused V10 tasks: five retention-only and five behavior-repair cases.
# Every cleanup trap appears in the fixed protocol and independent scorer.
TASKS = (
    TaskSpec("cleanup_v10_decision_retention_release_drift_04", "decision-retention", "single-module", "release_drift"),
    TaskSpec("cleanup_v10_decision_retention_split_owner_05", "decision-retention", "single-module", "split_owner"),
    TaskSpec("cleanup_v10_decision_retention_dynamic_retain_06", "decision-retention", "single-module", "dynamic_retain"),
    TaskSpec("cleanup_v10_decision_retention_semantic_duplicate_07", "decision-retention", "cross-module", "semantic_duplicate"),
    TaskSpec("cleanup_v10_decision_retention_dynamic_retain_18", "decision-retention", "integration", "dynamic_retain"),
    TaskSpec("cleanup_v10_repair_semantic_duplicate_23", "repair", "single-module", "semantic_duplicate"),
    TaskSpec("cleanup_v10_repair_release_drift_24", "repair", "single-module", "release_drift"),
    TaskSpec("cleanup_v10_repair_split_owner_29", "repair", "cross-module", "split_owner"),
    TaskSpec("cleanup_v10_repair_dynamic_retain_30", "repair", "cross-module", "dynamic_retain"),
    TaskSpec("cleanup_v10_repair_semantic_duplicate_35", "repair", "integration", "semantic_duplicate"),
)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_tasks() -> dict[str, dict[str, object]]:
    manifest_path = SOURCE_CORPUS / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or not isinstance(manifest.get("tasks"), list):
        raise ValueError("V10 source manifest has no task list")
    records: dict[str, dict[str, object]] = {}
    for raw in manifest["tasks"]:
        if not isinstance(raw, dict) or not isinstance(raw.get("task_id"), str):
            raise ValueError("V10 source manifest contains an invalid task")
        records[raw["task_id"]] = cast(dict[str, object], raw)
    return records


def copy_tree(source: Path, destination: Path) -> None:
    if not source.is_dir():
        raise FileNotFoundError(f"source tree is missing: {source}")
    shutil.copytree(source, destination)


def materialize_native_cleanup_effect_v5(corpus: Path) -> dict[str, object]:
    """Copy only the selected public, hidden, and reference V10 task trees."""
    if corpus.exists():
        raise FileExistsError(f"refusing to overwrite existing corpus: {corpus}")
    source = source_tasks()
    records: list[dict[str, object]] = []
    for task in TASKS:
        source_task = source.get(task.task_id)
        if source_task is None:
            raise ValueError(f"selected V10 task is missing: {task.task_id}")
        for field, expected in (("cohort", task.cohort), ("stratum", task.stratum), ("kind", task.kind)):
            if source_task.get(field) != expected:
                raise ValueError(f"selected V10 task metadata differs for {task.task_id}: {field}")
        workspace_path = Path(cast(str, source_task["workspace_path"]))
        hidden_path = Path(cast(str, source_task["hidden_tests_path"]))
        reference_path = Path(cast(str, source_task["reference_path"]))
        copy_tree(SOURCE_CORPUS / workspace_path, corpus / workspace_path)
        copy_tree(SOURCE_CORPUS / hidden_path, corpus / hidden_path)
        copy_tree(SOURCE_CORPUS / reference_path, corpus / reference_path)
        records.append(
            {
                "task_id": task.task_id,
                "cohort": task.cohort,
                "stratum": task.stratum,
                "kind": task.kind,
                "workspace_path": workspace_path.as_posix(),
                "hidden_tests_path": hidden_path.as_posix(),
                "reference_path": reference_path.as_posix(),
                "allowed_edit_paths": source_task["allowed_edit_paths"],
                "public_command": PUBLIC_COMMAND,
                "hidden_command": PUBLIC_COMMAND,
                "workspace_tree_sha256": tree_digest(corpus / workspace_path),
                "hidden_tests_tree_sha256": tree_digest(corpus / hidden_path),
                "reference_tree_sha256": tree_digest(corpus / reference_path),
            }
        )
    manifest: dict[str, object] = {
        "schema_version": 1,
        "corpus_id": "native-cleanup-effect-v5",
        "profile": "protocol-isolated-native-subset-of-v10",
        "source_corpus_manifest_sha256": file_sha256(SOURCE_CORPUS / "manifest.json"),
        "task_count": len(TASKS),
        "conditions": CONDITIONS,
        "task_contract": {
            "agent_visible": ["tasks/<task-id> only"],
            "hidden_after_agent_exit": True,
            "reference_never_available_to_agent": True,
            "checks": ["behavior", "owner_locality", "retirement_hygiene", "dynamic_retention", "documentation_drift"],
        },
        "tasks": records,
    }
    corpus.mkdir(parents=True, exist_ok=True)
    (corpus / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    _ = parser.add_argument("--corpus", required=True, type=Path)
    arguments = parser.parse_args()
    print(json.dumps(materialize_native_cleanup_effect_v5(arguments.corpus), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
