#!/usr/bin/env python3
"""Blindly score a multi-file repair workspace against injected hidden tests."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import cast


def command_from_json(value: str) -> list[str]:
    try:
        command = cast(object, json.loads(value))
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid command JSON: {error.msg}") from error
    if not isinstance(command, list):
        raise ValueError("command JSON must be a non-empty list of non-empty strings")
    parts = cast(list[object], command)
    if not parts or any(not isinstance(part, str) or not part for part in parts):
        raise ValueError("command JSON must be a non-empty list of non-empty strings")
    return [cast(str, part) for part in parts]


def test_environment() -> dict[str, str]:
    return {
        "PATH": os.environ.get("PATH", ""),
        "PYTHONNOUSERSITE": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
    }


def copy_tree(source: Path, destination: Path) -> None:
    _ = shutil.copytree(
        source,
        destination,
        ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
    )


def copy_hidden_tests(hidden_root: Path, candidate_root: Path) -> None:
    for source in sorted(hidden_root.rglob("*")):
        if source.is_dir():
            continue
        relative = source.relative_to(hidden_root)
        destination = candidate_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        _ = shutil.copy2(source, destination)


def score_workspace(workspace: Path, hidden_root: Path, command: list[str], *, timeout: float) -> dict[str, object]:
    """Run scorer-only tests in a copy so hidden files never enter agent artifacts."""
    try:
        with tempfile.TemporaryDirectory(prefix="adam-effect-v6-score-") as directory:
            candidate_root = Path(directory) / "candidate"
            copy_tree(workspace, candidate_root)
            copy_hidden_tests(hidden_root, candidate_root)
            result = subprocess.run(
                command,
                cwd=candidate_root,
                env=test_environment(),
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        return {
            "passed": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "timeout": False,
        }
    except subprocess.TimeoutExpired as error:
        return {
            "passed": False,
            "returncode": None,
            "stdout": error.stdout or "",
            "stderr": error.stderr or "",
            "timeout": True,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    _ = parser.add_argument("--workspace", type=Path, required=True)
    _ = parser.add_argument("--hidden-root", type=Path, required=True)
    _ = parser.add_argument("--command-json", required=True)
    _ = parser.add_argument("--timeout", type=float, default=15.0)
    arguments = cast(dict[str, object], vars(parser.parse_args()))
    report = score_workspace(
        cast(Path, arguments["workspace"]),
        cast(Path, arguments["hidden_root"]),
        command_from_json(cast(str, arguments["command_json"])),
        timeout=cast(float, arguments["timeout"]),
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
