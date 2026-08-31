from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import cast


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from materialize_effect_corpus_v9 import (  # noqa: E402
    EXPECTED_COHORTS,
    EXPECTED_STRATA,
    make_tasks,
    materialize,
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


class EffectCorpusV9Tests(unittest.TestCase):
    def test_forty_fresh_tasks_cover_both_cohorts_and_strata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            corpus = Path(directory) / "corpus"
            manifest = materialize(corpus)
            tasks = cast(list[dict[str, object]], manifest["tasks"])
            self.assertEqual(len(tasks), 40)
            self.assertEqual(len({str(task["task_id"]) for task in tasks}), 40)
            for cohort, expected in EXPECTED_COHORTS.items():
                selected = [task for task in tasks if task["cohort"] == cohort]
                self.assertEqual(len(selected), expected)
                self.assertEqual(
                    {stratum: sum(task["stratum"] == stratum for task in selected) for stratum in EXPECTED_STRATA},
                    EXPECTED_STRATA,
                )
            for task in tasks:
                workspace = corpus / str(task["workspace_path"])
                hidden = corpus / str(task["hidden_tests_path"])
                reference = corpus / str(task["reference_path"])
                self.assertEqual(tree_digest(workspace), task["workspace_tree_sha256"])
                self.assertEqual(tree_digest(hidden), task["hidden_tests_tree_sha256"])
                self.assertEqual(tree_digest(reference), task["reference_tree_sha256"])
                self.assertEqual([path.name for path in hidden.iterdir()], ["tests"])
                self.assertFalse((hidden / "policy.py").exists())

    def test_every_buggy_public_contract_fails_and_reference_passes_all_tests(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            corpus = Path(directory) / "corpus"
            _ = materialize(corpus)
            for task in make_tasks():
                with self.subTest(task=task.task_id):
                    public_result = run_suite(corpus / "tasks" / task.task_id)
                    self.assertNotEqual(public_result.returncode, 0, task.task_id)
                    reference_result = run_suite(corpus / "references" / task.task_id)
                    self.assertEqual(reference_result.returncode, 0, reference_result.stdout + reference_result.stderr)

    def test_manifest_is_deterministic_and_generator_refuses_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "one"
            second = Path(directory) / "two"
            _ = materialize(first)
            _ = materialize(second)
            self.assertEqual(
                hashlib.sha256((first / "manifest.json").read_bytes()).hexdigest(),
                hashlib.sha256((second / "manifest.json").read_bytes()).hexdigest(),
            )
            with self.assertRaises(FileExistsError):
                _ = materialize(first)


if __name__ == "__main__":
    _ = unittest.main()
