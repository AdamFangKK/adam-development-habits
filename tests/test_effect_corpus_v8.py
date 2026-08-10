"""Contract tests for the fresh V8 held-out repair corpus."""

# pyright: reportMissingTypeStubs=false

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
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from materialize_effect_corpus_v8 import EXPECTED_STRATA, make_tasks, materialize, tree_digest, write_tree  # noqa: E402


COMMAND = ["python3", "-m", "unittest", "discover", "-s", "tests"]


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


class EffectCorpusV8Tests(unittest.TestCase):
    def test_fresh_corpus_has_twenty_hash_linked_tasks_in_6_8_6_strata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            corpus = Path(directory) / "corpus"
            manifest = materialize(corpus)
            tasks = cast(list[dict[str, object]], manifest["tasks"])
            self.assertEqual(len(tasks), 20)
            self.assertEqual(
                {stratum: sum(str(task["stratum"]) == stratum for task in tasks) for stratum in EXPECTED_STRATA},
                EXPECTED_STRATA,
            )
            self.assertEqual(len({str(task["task_id"]) for task in tasks}), 20)
            self.assertTrue(all(not str(task["task_id"]).startswith(("cursor_", "config_", "canonical_", "tenant_")) for task in tasks))
            for task in tasks:
                public = corpus / str(task["workspace_path"])
                hidden = corpus / str(task["hidden_root_path"])
                self.assertEqual(tree_digest(public), task["workspace_tree_sha256"])
                self.assertEqual(tree_digest(hidden), task["hidden_tree_sha256"])
                self.assertFalse((public / "tests" / "test_hidden.py").exists())
                self.assertTrue((hidden / "tests" / "test_hidden.py").exists())

    def test_every_buggy_public_suite_fails_and_reference_hidden_suite_passes(self) -> None:
        tasks = make_tasks()
        with tempfile.TemporaryDirectory() as directory:
            corpus = Path(directory) / "corpus"
            _ = materialize(corpus)
            for task in tasks:
                with self.subTest(task=task.task_id):
                    public_root = corpus / "tasks" / task.task_id
                    self.assertNotEqual(run_suite(public_root).returncode, 0)
                    fixed_root = Path(directory) / "fixed" / task.task_id
                    write_tree(
                        fixed_root,
                        task.fixed
                        | {
                            "task.md": task.description,
                            "tests/test_public.py": task.public_test,
                            "tests/test_hidden.py": task.hidden_test,
                        },
                    )
                    result = run_suite(fixed_root)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_materialized_manifest_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "one"
            second = Path(directory) / "two"
            _ = materialize(first)
            _ = materialize(second)
            self.assertEqual(
                hashlib.sha256((first / "manifest.json").read_bytes()).hexdigest(),
                hashlib.sha256((second / "manifest.json").read_bytes()).hexdigest(),
            )


if __name__ == "__main__":
    _ = unittest.main()
