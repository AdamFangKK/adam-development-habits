#!/usr/bin/env python3
"""Replay a pinned Click regression from locally materialized source trees.

The runner does not download code. Callers supply the two exact upstream
source roots, which keeps the replay deterministic after acquisition and
prevents the package test suite from depending on the network.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import TypedDict


BUGGY_REVISION = "baea6233ea2f5b6c40f40edde6e297e25e3d2b94"
PATCH_REVISION = "986f322e435fac5e1fb8505d3683c8a224c18b06"
EXPECTED_TREES = {
    "buggy": "a953ff4164cec5751cc4d5edea2efaf56ad8a6bfd02e95342c858fc126db34d0",
    "patch": "33df2a40572feaece15d76176cce9967d8cec8218e837ee430dbf743db5f0287",
}
EXPECTED_TYPES = {
    "buggy": "9e09f7a8e687703bf278c176513e5024d369240015ac0f41463e2df31d713993",
    "patch": "e9911bc8d78de6755d8b8b9e044926e0959452bad62ac6ab7b5d2c6701b675f4",
}
CHECK_TIMEOUT_SECONDS = 10

BUGGY_RESOLUTION = """            if self.resolve_path:
                # realpath on Windows Python < 3.8 doesn't resolve symlinks
                if os.path.islink(rv):
                    rv = os.readlink(rv)

                rv = os.path.realpath(rv)
"""

PARTIAL_RESOLUTION = """            if self.resolve_path:
                dir_ = os.path.dirname(os.path.abspath(rv))

                if os.path.islink(rv):
                    rv = os.readlink(rv)

                rv = os.path.join(dir_, rv)
"""

OFFICIAL_RESOLUTION = """            if self.resolve_path:
                # Get the absolute directory containing the path.
                dir_ = os.path.dirname(os.path.abspath(rv))

                # Resolve a symlink. realpath on Windows Python < 3.9
                # doesn't resolve symlinks. This might return a relative
                # path even if the path to the link is absolute.
                if os.path.islink(rv):
                    rv = os.readlink(rv)

                # Join dir_ with the resolved symlink. If the resolved
                # path is relative, this will make it relative to the
                # original containing directory. If it is absolute, this
                # has no effect.
                rv = os.path.join(dir_, rv)
"""

BUGGY_ACCESS = """            if self.writable and not os.access(value, os.W_OK):
                self.fail(
                    _("{name} {filename!r} is not writable.").format(
                        name=self.name.title(), filename=os.fsdecode(value)
                    ),
                    param,
                    ctx,
                )
            if self.readable and not os.access(value, os.R_OK):
                self.fail(
                    _("{name} {filename!r} is not readable.").format(
                        name=self.name.title(), filename=os.fsdecode(value)
                    ),
                    param,
                    ctx,
                )
"""

OFFICIAL_ACCESS = """            if self.writable and not os.access(rv, os.W_OK):
                self.fail(
                    _("{name} {filename!r} is not writable.").format(
                        name=self.name.title(), filename=os.fsdecode(value)
                    ),
                    param,
                    ctx,
                )
            if self.readable and not os.access(rv, os.R_OK):
                self.fail(
                    _("{name} {filename!r} is not readable.").format(
                        name=self.name.title(), filename=os.fsdecode(value)
                    ),
                    param,
                    ctx,
                )
"""

PUBLIC_TEST = r'''
import os
import tempfile
import unittest

import click


class PublicUpstreamRegression(unittest.TestCase):
    def test_relative_and_absolute_links_resolve_to_the_target(self):
        with tempfile.TemporaryDirectory() as tempdir:
            target = os.path.join(tempdir, "test_file")
            os.makedirs(os.path.join(tempdir, "links"), exist_ok=True)
            open(target, "w", encoding="utf-8").close()
            cases = (
                ("relative_link", os.path.basename(target)),
                (os.path.join("links", "absolute_link"), target),
            )
            for link_name, link_target in cases:
                with self.subTest(link_name=link_name):
                    link = os.path.join(tempdir, link_name)
                    os.symlink(link_target, link)
                    ctx = click.Context(click.Command("do_stuff"))
                    actual = click.Path(resolve_path=True).convert(link, None, ctx)
                    self.assertEqual(actual, target)


unittest.main()
'''

HIDDEN_TEST = r'''
import os
import tempfile
import unittest
from unittest.mock import patch

import click


class ResolvedAccessContract(unittest.TestCase):
    def test_access_checks_receive_the_resolved_target(self):
        with tempfile.TemporaryDirectory() as tempdir:
            target = os.path.join(tempdir, "target")
            link = os.path.join(tempdir, "relative_link")
            open(target, "w", encoding="utf-8").close()
            os.symlink(os.path.basename(target), link)
            original_access = os.access
            observed = []

            def record_access(path, mode):
                observed.append(path)
                return original_access(path, mode)

            with patch.object(click.types.os, "access", side_effect=record_access):
                ctx = click.Context(click.Command("do_stuff"))
                actual = click.Path(resolve_path=True, writable=True, readable=True).convert(link, None, ctx)

            self.assertEqual(actual, target)
            self.assertEqual(observed, [target, target])


unittest.main()
'''


class CheckResult(TypedDict):
    exit_code: int
    passed: bool
    summary: str


class VariantResult(TypedDict):
    source_tree_sha256: str
    types_sha256: str
    public: CheckResult
    hidden: CheckResult
    passed: bool


class ReplayReport(TypedDict):
    schema_version: int
    source: dict[str, str]
    protocol: dict[str, str | bool]
    tool: dict[str, str]
    variants: dict[str, VariantResult]
    conclusion: dict[str, str | bool]


class Arguments(argparse.Namespace):
    bug_root: Path = Path()
    patch_root: Path = Path()
    output: Path | None = None


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_tree_sha256(click_root: Path) -> str:
    digest = hashlib.sha256()
    files = sorted(
        (path for path in click_root.rglob("*") if path.is_file() and "__pycache__" not in path.parts),
        key=lambda path: path.relative_to(click_root).as_posix(),
    )
    for path in files:
        digest.update(path.relative_to(click_root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def source_root(root: Path, label: str) -> Path:
    click_root = root.resolve() / "src" / "click"
    types_path = click_root / "types.py"
    if not types_path.is_file():
        raise ValueError(f"{label} source must contain src/click/types.py")

    actual_tree = source_tree_sha256(click_root)
    if actual_tree != EXPECTED_TREES[label]:
        raise ValueError(f"{label} source tree SHA-256 does not match the pinned release")
    if sha256(types_path) != EXPECTED_TYPES[label]:
        raise ValueError(f"{label} types.py SHA-256 does not match the pinned release")
    return click_root


def test_environment(root: Path, program: str, timeout_seconds: float = CHECK_TIMEOUT_SECONDS) -> CheckResult:
    source_click_root = root / "src" / "click"
    expected_tree = source_tree_sha256(source_click_root)
    with tempfile.TemporaryDirectory(prefix="adam-click-execution-") as temporary_directory:
        workspace = Path(temporary_directory)
        library = workspace / "library"
        copied_click_root = library / "click"
        _ = shutil.copytree(source_click_root, copied_click_root, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        if source_tree_sha256(copied_click_root) != expected_tree:
            return {
                "exit_code": 1,
                "passed": False,
                "summary": "validated click source changed before isolated execution",
            }

        environment = {
            "PATH": os.environ.get("PATH", ""),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
            "PYTHONPATH": str(library),
        }
        try:
            result = subprocess.run(
                [sys.executable, "-s", "-c", program],
                cwd=workspace,
                capture_output=True,
                check=False,
                env=environment,
                text=True,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            return {
                "exit_code": 124,
                "passed": False,
                "summary": f"timed out after {timeout_seconds:g} seconds",
            }

    output = (result.stderr or result.stdout).strip().splitlines()
    return {
        "exit_code": result.returncode,
        "passed": result.returncode == 0,
        "summary": output[-1] if output else "no output",
    }


def replace_once(source: str, old: str, new: str, description: str) -> str:
    if source.count(old) != 1:
        raise ValueError(f"could not apply {description} exactly once")
    return source.replace(old, new)


def materialize_variant(bug_root: Path, workspace: Path, name: str) -> Path:
    candidate_root = workspace / name
    _ = shutil.copytree(bug_root, candidate_root, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    types_path = candidate_root / "src" / "click" / "types.py"
    source = types_path.read_text(encoding="utf-8")

    if name == "partial-repair":
        source = replace_once(source, BUGGY_RESOLUTION, PARTIAL_RESOLUTION, "partial resolution patch")
    elif name == "official-fixed":
        source = replace_once(source, BUGGY_RESOLUTION, OFFICIAL_RESOLUTION, "official resolution patch")
        source = replace_once(source, BUGGY_ACCESS, OFFICIAL_ACCESS, "official access patch")
    else:
        raise ValueError(f"unknown variant: {name}")

    _ = types_path.write_text(source, encoding="utf-8")
    return candidate_root


def require_symlink_support() -> None:
    with tempfile.TemporaryDirectory(prefix="adam-click-symlink-") as temporary_directory:
        directory = Path(temporary_directory)
        target = directory / "target"
        link = directory / "link"
        _ = target.write_text("", encoding="utf-8")
        try:
            os.symlink(target.name, link)
        except OSError as error:
            raise RuntimeError("the Click replay requires local symlink creation support") from error
        if not link.is_symlink():
            raise RuntimeError("the Click replay requires local symlink creation support")


def run_variant(root: Path) -> VariantResult:
    click_root = root / "src" / "click"
    public = test_environment(root, PUBLIC_TEST)
    hidden = test_environment(root, HIDDEN_TEST)
    return {
        "source_tree_sha256": source_tree_sha256(click_root),
        "types_sha256": sha256(click_root / "types.py"),
        "public": public,
        "hidden": hidden,
        "passed": public["passed"] and hidden["passed"],
    }


def replay(bug_root: Path, patch_root: Path) -> ReplayReport:
    require_symlink_support()
    bug_click_root = source_root(bug_root, "buggy")
    patch_click_root = source_root(patch_root, "patch")
    with tempfile.TemporaryDirectory(prefix="adam-click-replay-") as temporary_directory:
        workspace = Path(temporary_directory)
        partial_root = materialize_variant(bug_root, workspace, "partial-repair")
        official_root = materialize_variant(bug_root, workspace, "official-fixed")
        official_click_root = official_root / "src" / "click"

        if sha256(official_click_root / "types.py") != sha256(patch_click_root / "types.py"):
            raise AssertionError("the reconstructed causal owner does not match the pinned official patch")

        variants = {
            "buggy-8.0.1": run_variant(bug_root),
            "partial-repair": run_variant(partial_root),
            "official-owner-patch": run_variant(official_root),
            "official-patch": run_variant(patch_root),
        }
    expected = {
        "buggy-8.0.1": (False, False),
        "partial-repair": (True, False),
        "official-owner-patch": (True, True),
        "official-patch": (True, True),
    }
    for name, (public_passed, hidden_passed) in expected.items():
        result = variants[name]
        if result["public"]["passed"] != public_passed or result["hidden"]["passed"] != hidden_passed:
            raise AssertionError(f"{name} did not produce the expected public and hidden outcomes")

    return {
        "schema_version": 1,
        "source": {
            "repository": "https://github.com/pallets/click",
            "buggy_revision": BUGGY_REVISION,
            "official_patch_revision": PATCH_REVISION,
            "buggy_click_tree_sha256": source_tree_sha256(bug_click_root),
            "patch_click_tree_sha256": source_tree_sha256(patch_click_root),
            "buggy_types_sha256": sha256(bug_click_root / "types.py"),
            "patch_types_sha256": sha256(patch_click_root / "types.py"),
        },
        "protocol": {
            "public_contract": "Adapted from Click tests/test_types.py test_symlink_resolution; it checks relative and absolute symlink resolution at the Path public boundary.",
            "hidden_contract": "Checks that readable and writable access checks receive the resolved target rather than the original symlink input.",
            "candidate_scope": "Only src/click/types.py changes in generated candidate trees; source inputs and test programs remain outside candidate control. Every supplied source tree is independently hash-validated, and test subprocesses receive only a fresh copy of the validated click package.",
            "offline_after_materialization": True,
            "platform_requirement": "POSIX-style symlink support is required.",
        },
        "tool": {
            "path": "scripts/replay_external_click.py",
            "sha256": sha256(Path(__file__).resolve()),
            "python": sys.version.split()[0],
            "platform": sys.platform,
        },
        "variants": variants,
        "conclusion": {
            "protocol_effective": True,
            "claim": "The hidden contract rejects a plausible partial repair that passes the public regression, while the official repair passes both.",
            "not_proven": "This one regression protocol does not estimate model repair-success uplift, general causal reasoning, Windows behavior, or production safety.",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay the pinned Click symlink regression offline.")
    _ = parser.add_argument("--bug-root", required=True, type=Path, help="Materialized Click 8.0.1 source root")
    _ = parser.add_argument("--patch-root", required=True, type=Path, help="Materialized official Click patch source root")
    _ = parser.add_argument("--output", type=Path, help="Optional JSON report path")
    arguments = parser.parse_args(namespace=Arguments())
    report = replay(arguments.bug_root, arguments.patch_root)
    serialized = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if arguments.output is not None:
        _ = arguments.output.write_text(serialized, encoding="utf-8")
    print(serialized, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
