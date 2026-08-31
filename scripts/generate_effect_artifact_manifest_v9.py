#!/usr/bin/env python3
"""Create a deterministic, append-only manifest for V9 raw experiment artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import cast


REQUIRED_ARTIFACTS = (
    "agent.stdout.log",
    "agent.stderr.log",
    "agent-output.md",
    "candidate.diff",
    "public.json",
    "hidden-score.json",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_object(path: Path) -> dict[str, object]:
    value = cast(object, json.loads(path.read_text(encoding="utf-8")))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return cast(dict[str, object], value)


def generate(raw_root: Path, result_path: Path, output_path: Path) -> dict[str, object]:
    if output_path.exists() or output_path.is_symlink():
        raise FileExistsError(f"refusing to overwrite existing manifest: {output_path}")
    result = load_object(result_path)
    trials = result.get("trials")
    if not isinstance(trials, list):
        raise ValueError("result.trials must be a list")
    entries: list[dict[str, object]] = []
    for index, value in enumerate(cast(list[object], trials)):
        if not isinstance(value, dict):
            raise ValueError(f"result.trials[{index}] must be an object")
        trial = cast(dict[str, object], value)
        relative_artifact = trial.get("artifact_path")
        if not isinstance(relative_artifact, str) or not relative_artifact or Path(relative_artifact).is_absolute() or ".." in Path(relative_artifact).parts:
            raise ValueError(f"result.trials[{index}].artifact_path must be relative")
        artifact_root = raw_root / relative_artifact
        if not artifact_root.is_dir() or artifact_root.is_symlink():
            raise ValueError(f"artifact directory is missing or unsafe: {relative_artifact}")
        files: list[dict[str, str]] = []
        for filename in REQUIRED_ARTIFACTS:
            path = artifact_root / filename
            if not path.is_file() or path.is_symlink():
                raise ValueError(f"missing artifact: {relative_artifact}/{filename}")
            files.append({"path": f"{relative_artifact}/{filename}", "sha256": sha256(path)})
        entries.append({
            "task_id": trial.get("task_id"),
            "condition": trial.get("condition"),
            "cohort": trial.get("cohort"),
            "stratum": trial.get("stratum"),
            "execution_order": trial.get("execution_order"),
            "replicate_index": trial.get("replicate_index"),
            "trial_complete": trial.get("trial_complete"),
            "hidden_repair_pass": trial.get("hidden_repair_pass"),
            "implementation_integrity_passed": trial.get("implementation_integrity_passed"),
            "files": files,
        })
    entries.sort(key=lambda entry: (str(entry.get("task_id")), int(cast(int, entry.get("execution_order", 0)))))
    manifest: dict[str, object] = {
        "schema_version": 1,
        "manifest_type": "effect-artifacts-v9",
        "source_result": result_path.name,
        "source_result_sha256": sha256(result_path),
        "raw_root": raw_root.name,
        "trial_count": len(entries),
        "required_artifacts": list(REQUIRED_ARTIFACTS),
        "entries": entries,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _ = output_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    _ = parser.add_argument("--raw-root", type=Path, required=True)
    _ = parser.add_argument("--result", type=Path, required=True)
    _ = parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    print(json.dumps(generate(arguments.raw_root, arguments.result, arguments.output), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
