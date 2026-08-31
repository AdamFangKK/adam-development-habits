#!/usr/bin/env python3
"""Blindly score a V9 candidate without allowing reference-source injection."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import cast


def command_from_json(value: str) -> list[str]:
    parsed = cast(object, json.loads(value))
    if not isinstance(parsed, list):
        raise ValueError("command JSON must be a non-empty list of non-empty strings")
    parts = cast(list[object], parsed)
    if not parts or any(not isinstance(part, str) or not part for part in parts):
        raise ValueError("command JSON must be a non-empty list of non-empty strings")
    return [cast(str, part) for part in parts]


def paths_from_json(value: str) -> tuple[str, ...]:
    parsed = cast(object, json.loads(value))
    if not isinstance(parsed, list):
        raise ValueError("allowed paths JSON must be a non-empty list")
    paths = cast(list[object], parsed)
    if not paths or any(
        not isinstance(path, str)
        or not path
        or Path(path).is_absolute()
        or ".." in Path(path).parts
        for path in paths
    ):
        raise ValueError("allowed paths must be non-empty repository-relative paths")
    return tuple(cast(str, path) for path in paths)


def test_environment() -> dict[str, str]:
    return {
        "PATH": os.environ.get("PATH", ""),
        "PYTHONNOUSERSITE": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
    }


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def implementation_hashes(root: Path, allowed_paths: tuple[str, ...]) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for relative in allowed_paths:
        path = root / relative
        if path.is_symlink():
            raise ValueError(f"allowed implementation path is a symbolic link: {relative}")
        if not path.exists():
            hashes[relative] = "<missing>"
            continue
        if not path.is_file():
            raise ValueError(f"allowed implementation path is not a regular file: {relative}")
        hashes[relative] = sha256(path)
    return hashes


def ensure_regular_tree(root: Path, label: str) -> None:
    if root.is_symlink() or not root.is_dir():
        raise ValueError(f"{label} must be a real directory")
    for path in root.rglob("*"):
        if path.is_symlink():
            raise ValueError(f"{label} must not contain symbolic links")
        if not path.is_dir() and not path.is_file():
            raise ValueError(f"{label} must contain only regular files and directories")


def copy_workspace(source: Path, destination: Path) -> None:
    ensure_regular_tree(source, "workspace")
    _ = shutil.copytree(
        source,
        destination,
        ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
    )


def inject_hidden_tests(hidden_root: Path, candidate_root: Path) -> list[str]:
    ensure_regular_tree(hidden_root, "hidden-test root")
    tests_root = hidden_root / "tests"
    if not tests_root.is_dir() or tests_root.is_symlink():
        raise ValueError("hidden-test root must contain a real tests directory")
    unexpected = [path for path in hidden_root.iterdir() if path.name != "tests"]
    if unexpected:
        raise ValueError("hidden-test root may contain only the tests directory")

    injected: list[str] = []
    for source in sorted(path for path in tests_root.rglob("*") if path.is_file()):
        relative = source.relative_to(hidden_root)
        destination = candidate_root / relative
        if destination.exists() or destination.is_symlink():
            raise ValueError(f"hidden test collides with candidate path: {relative.as_posix()}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        _ = shutil.copy2(source, destination)
        injected.append(relative.as_posix())
    if not injected:
        raise ValueError("hidden-test root contains no test files")
    return injected


def score_workspace(
    workspace: Path,
    hidden_root: Path,
    allowed_paths: tuple[str, ...],
    command: list[str],
    *,
    timeout: float,
) -> dict[str, object]:
    """Score in a temporary copy and prove hidden injection did not alter implementation bytes."""
    try:
        with tempfile.TemporaryDirectory(prefix="adam-effect-v9-score-") as directory:
            candidate_root = Path(directory) / "candidate"
            copy_workspace(workspace, candidate_root)
            before = implementation_hashes(candidate_root, allowed_paths)
            injected = inject_hidden_tests(hidden_root, candidate_root)
            after = implementation_hashes(candidate_root, allowed_paths)
            integrity = before == after
            if not integrity:
                raise ValueError("hidden-test injection changed implementation bytes")
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
            "passed": result.returncode == 0 and integrity,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "timeout": False,
            "implementation_integrity_passed": integrity,
            "implementation_sha256": before,
            "injected_hidden_tests": injected,
        }
    except subprocess.TimeoutExpired as error:
        return {
            "passed": False,
            "returncode": None,
            "stdout": error.stdout or "",
            "stderr": error.stderr or "",
            "timeout": True,
            "implementation_integrity_passed": False,
        }
    except (OSError, ValueError) as error:
        return {
            "passed": False,
            "returncode": None,
            "stdout": "",
            "stderr": f"{type(error).__name__}: {error}",
            "timeout": False,
            "implementation_integrity_passed": False,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    _ = parser.add_argument("--workspace", type=Path, required=True)
    _ = parser.add_argument("--hidden-root", type=Path, required=True)
    _ = parser.add_argument("--allowed-paths-json", required=True)
    _ = parser.add_argument("--command-json", required=True)
    _ = parser.add_argument("--timeout", type=float, default=15.0)
    arguments = cast(dict[str, object], vars(parser.parse_args()))
    report = score_workspace(
        cast(Path, arguments["workspace"]),
        cast(Path, arguments["hidden_root"]),
        paths_from_json(cast(str, arguments["allowed_paths_json"])),
        command_from_json(cast(str, arguments["command_json"])),
        timeout=cast(float, arguments["timeout"]),
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
