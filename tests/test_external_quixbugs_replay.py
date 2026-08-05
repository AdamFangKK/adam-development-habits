from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import cast


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples" / "external-quixbugs-fixture"
HIDDEN_CHECK = ROOT / "examples" / "external-quixbugs-hidden-check.py"
REFERENCE = ROOT / "examples" / "external-quixbugs-verifier-reference.py"
REPLAY_REPORT = ROOT / "examples" / "external-quixbugs-replay.json"
CANDIDATES = {
    "baseline": ROOT / "examples" / "external-quixbugs-baseline.py",
    "skill-guided": ROOT / "examples" / "external-quixbugs-skill.py",
}

PINNED_HASHES = {
    FIXTURE / "python_programs" / "shortest_paths.py": "e99679a54634bc940a78c1f211e6126f5119a7654a089d1f56f264a1deaa0ce2",
    FIXTURE / "python_testcases" / "test_shortest_paths.py": "8ee521556000dc6bcf4ae71c6db0f91c387f96e055557ec1accdde824928b4f8",
    FIXTURE / "conftest.py": "e8325790da8f5d06af1251e724838c7c8f3c8a18d90c31ddc9d24d9f3aa57ce8",
    CANDIDATES["baseline"]: "57575618e1d5622c77f53596b42d8b3cc86553e83edaa24fb5eed917d1717aa0",
    CANDIDATES["skill-guided"]: "bfb967b7551737317017c161dd082d4931427c44f8db6d6fade177162111d0b4",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_object(path: Path) -> dict[str, object]:
    return parse_object(path.read_text(encoding="utf-8"), str(path))


def parse_object(text: str, name: str) -> dict[str, object]:
    value = cast(object, json.loads(text))
    if not isinstance(value, dict):
        raise AssertionError(f"{name} must contain a JSON object")
    return cast(dict[str, object], value)


def require_object(value: object, name: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise AssertionError(f"{name} must be an object")
    return cast(dict[str, object], value)


def require_text(value: object, name: str) -> str:
    if not isinstance(value, str):
        raise AssertionError(f"{name} must be text")
    return value


def run_public_tests(root: Path) -> subprocess.CompletedProcess[str]:
    environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "-q", "python_testcases/test_shortest_paths.py"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
        env=environment,
    )


class ExternalQuixBugsReplayTests(unittest.TestCase):
    def test_sanitized_fixture_matches_the_pinned_public_upstream_files(self) -> None:
        for path, expected in PINNED_HASHES.items():
            with self.subTest(path=path):
                self.assertEqual(sha256(path), expected)

    def test_pristine_buggy_fixture_reproduces_three_public_failures(self) -> None:
        result = run_public_tests(FIXTURE)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("3 failed", result.stdout)

    def test_replay_report_hashes_the_local_inputs(self) -> None:
        report = load_object(REPLAY_REPORT)
        source = require_object(report["source"], "source")
        replay = require_object(report["replay"], "replay")
        self.assertEqual(require_text(source["fixture_source_sha256"], "fixture source hash"), sha256(FIXTURE / "python_programs" / "shortest_paths.py"))
        self.assertEqual(require_text(source["fixture_public_test_sha256"], "fixture test hash"), sha256(FIXTURE / "python_testcases" / "test_shortest_paths.py"))
        self.assertEqual(require_text(source["fixture_conftest_sha256"], "fixture conftest hash"), sha256(FIXTURE / "conftest.py"))
        verifier_reference = require_object(replay["verifier_reference"], "verifier reference")
        self.assertEqual(require_text(verifier_reference["sha256"], "verifier reference hash"), sha256(REFERENCE))
        hidden_check = require_object(replay["hidden_check"], "hidden check")
        self.assertEqual(require_text(hidden_check["sha256"], "hidden check hash"), sha256(HIDDEN_CHECK))

    def test_recorded_candidates_replay_the_public_and_hidden_results(self) -> None:
        for label, candidate in CANDIDATES.items():
            with self.subTest(candidate=label), tempfile.TemporaryDirectory(prefix="adam-quixbugs-replay-") as temporary_directory:
                candidate_root = Path(temporary_directory) / "fixture"
                _ = shutil.copytree(FIXTURE, candidate_root)
                candidate_target = candidate_root / "python_programs" / "shortest_paths.py"
                _ = shutil.copyfile(candidate, candidate_target)

                public = run_public_tests(candidate_root)
                self.assertEqual(public.returncode, 0, public.stdout + public.stderr)
                self.assertIn("3 passed", public.stdout)

                hidden = subprocess.run(
                    [
                        sys.executable,
                        str(HIDDEN_CHECK),
                        "--candidate",
                        str(candidate_target),
                        "--reference",
                        str(REFERENCE),
                        "--label",
                        label,
                    ],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(hidden.returncode, 0, hidden.stdout + hidden.stderr)
                report = parse_object(hidden.stdout, f"hidden report for {label}")
                self.assertEqual(require_text(report["candidate_sha256"], "candidate hash"), sha256(candidate))
                self.assertEqual(report["case_count"], 2)
                self.assertTrue(report["input_mapping_unchanged"])


if __name__ == "__main__":
    _ = unittest.main()
