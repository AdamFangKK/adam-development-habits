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
sys.path.insert(0, str(ROOT / "scripts"))

from materialize_effect_corpus_v9 import (  # noqa: E402
    EXPECTED_COHORTS,
    EXPECTED_STRATA,
    cleanup_v10_tasks,
    materialize_cleanup_v10,
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


class CleanupEffectCorpusV10Tests(unittest.TestCase):
    def test_materialization_is_deterministic_and_has_all_adversarial_kinds(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first"
            second = Path(directory) / "second"
            first_manifest = materialize_cleanup_v10(first)
            second_manifest = materialize_cleanup_v10(second)
            self.assertEqual(
                hashlib.sha256((first / "manifest.json").read_bytes()).hexdigest(),
                hashlib.sha256((second / "manifest.json").read_bytes()).hexdigest(),
            )
            self.assertEqual(first_manifest, second_manifest)
            tasks = cast(list[dict[str, object]], first_manifest["tasks"])
            self.assertEqual(len(tasks), 40)
            self.assertEqual(
                {str(task["kind"]) for task in tasks},
                {"split_owner", "dynamic_retain", "semantic_duplicate", "release_drift"},
            )
            self.assertEqual(
                {kind: sum(task["kind"] == kind for task in tasks) for kind in {"split_owner", "dynamic_retain", "semantic_duplicate", "release_drift"}},
                {"split_owner": 10, "dynamic_retain": 10, "semantic_duplicate": 10, "release_drift": 10},
            )
            for cohort, expected in EXPECTED_COHORTS.items():
                selected = [task for task in tasks if task["cohort"] == cohort]
                self.assertEqual(len(selected), expected)
                self.assertEqual(
                    {stratum: sum(task["stratum"] == stratum for task in selected) for stratum in EXPECTED_STRATA},
                    EXPECTED_STRATA,
                )
            for task in tasks:
                hidden = first / str(task["hidden_tests_path"])
                reference = first / str(task["reference_path"])
                allowed_paths = cast(list[str], task["allowed_edit_paths"])
                self.assertEqual(tree_digest(hidden), task["hidden_tests_tree_sha256"])
                self.assertEqual(tree_digest(reference), task["reference_tree_sha256"])
                self.assertFalse((hidden / "policy.py").exists())
                self.assertIn("README.md", allowed_paths)
                self.assertIn(f"docs/{task['task_id']}.md", allowed_paths)

    def test_hidden_contract_rejects_shallow_repairs_and_accepts_reference_fixes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            corpus = Path(directory) / "corpus"
            materialize_cleanup_v10(corpus)
            for task in cleanup_v10_tasks():
                with self.subTest(task=task.task_id, phase="initial"):
                    workspace = corpus / "tasks" / task.task_id
                    self.assertEqual(run_suite(workspace).returncode, 0, task.task_id)
                    candidate = Path(directory) / "initial" / task.task_id
                    candidate.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copytree(workspace, candidate)
                    _ = shutil.copy2(
                        corpus / "hidden-tests" / task.task_id / "tests" / "test_hidden.py",
                        candidate / "tests" / "test_hidden.py",
                    )
                    self.assertNotEqual(run_suite(candidate).returncode, 0, task.task_id)

                with self.subTest(task=task.task_id, phase="policy_only"):
                    shallow = Path(directory) / "shallow" / task.task_id
                    shallow.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copytree(corpus / "tasks" / task.task_id, shallow)
                    _ = shutil.copy2(corpus / "references" / task.task_id / "policy.py", shallow / "policy.py")
                    _ = shutil.copy2(
                        corpus / "hidden-tests" / task.task_id / "tests" / "test_hidden.py",
                        shallow / "tests" / "test_hidden.py",
                    )
                    self.assertNotEqual(run_suite(shallow).returncode, 0, task.task_id)

                with self.subTest(task=task.task_id, phase="reference"):
                    self.assertEqual(run_suite(corpus / "references" / task.task_id).returncode, 0, task.task_id)

    def test_dynamic_registry_is_a_real_retention_constraint(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            corpus = Path(directory) / "corpus"
            materialize_cleanup_v10(corpus)
            dynamic = next(task for task in cleanup_v10_tasks() if task.kind == "dynamic_retain")
            reference = corpus / "references" / dynamic.task_id
            self.assertTrue((reference / f"plugins/{dynamic.task_id}_adapter.py").is_file())
            self.assertTrue((reference / f"runtime/{dynamic.task_id}.json").is_file())
            self.assertEqual(run_suite(reference).returncode, 0, dynamic.task_id)

    def test_dynamic_registry_retarget_cannot_replace_the_retained_adapter(self) -> None:
        """A passing substitute must not erase the named external compatibility path."""
        with tempfile.TemporaryDirectory() as directory:
            corpus = Path(directory) / "corpus"
            materialize_cleanup_v10(corpus)
            dynamic = next(task for task in cleanup_v10_tasks() if task.kind == "dynamic_retain")
            candidate = Path(directory) / "candidate"
            shutil.copytree(corpus / "references" / dynamic.task_id, candidate)

            policy = candidate / "policy.py"
            _ = policy.write_text(
                policy.read_text(encoding="utf-8")
                + "\n\ndef normalize(value):\n    return canonical_normalize(value)\n",
                encoding="utf-8",
            )
            (candidate / f"plugins/{dynamic.task_id}_adapter.py").unlink()
            _ = (candidate / f"runtime/{dynamic.task_id}.json").write_text(
                json.dumps({"adapter": "policy"}, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            _ = shutil.copy2(
                corpus / "hidden-tests" / dynamic.task_id / "tests" / "test_hidden.py",
                candidate / "tests" / "test_hidden.py",
            )

            result = run_suite(candidate)
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_hidden_contract_accepts_equivalent_current_contract_wording(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            corpus = Path(directory) / "corpus"
            materialize_cleanup_v10(corpus)
            dynamic = next(task for task in cleanup_v10_tasks() if task.kind == "dynamic_retain")
            candidate = Path(directory) / "candidate"
            shutil.copytree(corpus / "tasks" / dynamic.task_id, candidate)
            old_marker = f"legacy_contract_{dynamic.task_id}"
            for path in candidate.rglob("*"):
                if path.is_file() and "tests" not in path.parts:
                    _ = path.write_text(
                        path.read_text(encoding="utf-8").replace(old_marker, f"current_contract_{dynamic.task_id}"),
                        encoding="utf-8",
                    )
            _ = shutil.copy2(
                corpus / "hidden-tests" / dynamic.task_id / "tests" / "test_hidden.py",
                candidate / "tests" / "test_hidden.py",
            )
            self.assertEqual(run_suite(candidate).returncode, 0, dynamic.task_id)


if __name__ == "__main__":
    _ = unittest.main()
