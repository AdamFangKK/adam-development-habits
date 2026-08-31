from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATIC_CORPUS = ROOT / "examples" / "effect-corpus-v9-cleanup"
sys.path.insert(0, str(ROOT / "scripts"))

from materialize_effect_corpus_v9 import (  # noqa: E402
    EXPECTED_COHORTS,
    EXPECTED_STRATA,
    cleanup_tasks,
    materialize_cleanup,
    tree_digest,
)


COMMAND = [sys.executable, "-m", "unittest", "discover", "-s", "tests"]


def run_suite(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        COMMAND,
        cwd=root,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1"},
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )


class CleanupEffectCorpusTests(unittest.TestCase):
    def test_committed_cleanup_corpus_matches_generator_manifest(self) -> None:
        self.assertTrue(STATIC_CORPUS.is_dir())
        with tempfile.TemporaryDirectory() as directory:
            generated = Path(directory) / "corpus"
            materialize_cleanup(generated)
            self.assertEqual(
                hashlib.sha256((generated / "manifest.json").read_bytes()).hexdigest(),
                hashlib.sha256((STATIC_CORPUS / "manifest.json").read_bytes()).hexdigest(),
            )
            for relative in ("tasks", "hidden-tests", "references"):
                self.assertEqual(tree_digest(generated / relative), tree_digest(STATIC_CORPUS / relative))

    def test_cleanup_profile_materializes_stable_split_and_all_trap_kinds(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first"
            second = Path(directory) / "second"
            first_manifest = materialize_cleanup(first)
            second_manifest = materialize_cleanup(second)
            self.assertEqual(
                hashlib.sha256((first / "manifest.json").read_bytes()).hexdigest(),
                hashlib.sha256((second / "manifest.json").read_bytes()).hexdigest(),
            )
            self.assertEqual(first_manifest, second_manifest)
            tasks = first_manifest["tasks"]
            self.assertEqual(len(tasks), 40)
            self.assertEqual(
                {str(task["kind"]) for task in tasks},
                {"replace", "duplicate", "retain", "docs"},
            )
            for cohort, expected in EXPECTED_COHORTS.items():
                selected = [task for task in tasks if task["cohort"] == cohort]
                self.assertEqual(len(selected), expected)
                self.assertEqual(
                    {stratum: sum(task["stratum"] == stratum for task in selected) for stratum in EXPECTED_STRATA},
                    EXPECTED_STRATA,
                )
            self.assertEqual(first_manifest["profile"], "cleanup")
            self.assertTrue(first_manifest["cleanup_contract"]["reference_implementation_is_not_available_to_agent"])
            for task in tasks:
                hidden = first / str(task["hidden_tests_path"])
                reference = first / str(task["reference_path"])
                self.assertEqual(tree_digest(hidden), task["hidden_tests_tree_sha256"])
                self.assertEqual(tree_digest(reference), task["reference_tree_sha256"])
                self.assertFalse((hidden / "policy.py").exists())

    def test_public_tests_deliberately_miss_retirement_but_hidden_contract_catches_it(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "corpus"
            materialize_cleanup(root)
            for task in cleanup_tasks():
                with self.subTest(task=task.task_id):
                    workspace = root / "tasks" / task.task_id
                    public = run_suite(workspace)
                    if task.cohort == "repair":
                        self.assertNotEqual(public.returncode, 0, task.task_id)
                    else:
                        self.assertEqual(public.returncode, 0, public.stdout + public.stderr)

                    candidate = Path(directory) / "candidates" / task.task_id
                    candidate.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copytree(workspace, candidate)
                    _ = shutil.copy2(
                        root / "hidden-tests" / task.task_id / "tests" / "test_hidden.py",
                        candidate / "tests" / "test_hidden.py",
                    )
                    hidden = run_suite(candidate)
                    self.assertNotEqual(hidden.returncode, 0, task.task_id)

    def test_all_reference_fixes_pass_public_and_hidden_contracts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "corpus"
            materialize_cleanup(root)
            for task in cleanup_tasks():
                with self.subTest(task=task.task_id):
                    result = run_suite(root / "references" / task.task_id)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    _ = unittest.main()
