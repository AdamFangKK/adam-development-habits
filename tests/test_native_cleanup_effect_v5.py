from __future__ import annotations

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

from materialize_effect_corpus_v9 import tree_digest  # noqa: E402
from materialize_native_cleanup_effect_v5 import TASKS, materialize_native_cleanup_effect_v5  # noqa: E402


COMMAND = [sys.executable, "-m", "unittest", "discover", "-s", "tests"]
V4_TASK_IDS = {
    "cleanup_v10_decision_retention_split_owner_01",
    "cleanup_v10_decision_retention_dynamic_retain_02",
    "cleanup_v10_decision_retention_semantic_duplicate_03",
    "cleanup_v10_decision_retention_release_drift_08",
    "cleanup_v10_decision_retention_dynamic_retain_10",
    "cleanup_v10_repair_split_owner_21",
    "cleanup_v10_repair_dynamic_retain_22",
    "cleanup_v10_repair_semantic_duplicate_27",
    "cleanup_v10_repair_release_drift_28",
    "cleanup_v10_repair_split_owner_37",
}


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


class NativeCleanupEffectV5Tests(unittest.TestCase):
    def test_subset_is_deterministic_and_covers_every_cleanup_trap(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first"
            second = Path(directory) / "second"
            first_manifest = materialize_native_cleanup_effect_v5(first)
            second_manifest = materialize_native_cleanup_effect_v5(second)
            self.assertEqual(first_manifest, second_manifest)
            tasks = cast(list[dict[str, object]], first_manifest["tasks"])
            self.assertEqual(len(tasks), 10)
            self.assertEqual({task["kind"] for task in tasks}, {"split_owner", "dynamic_retain", "semantic_duplicate", "release_drift"})
            self.assertEqual({task["cohort"] for task in tasks}, {"decision-retention", "repair"})
            self.assertEqual(sum(task["cohort"] == "decision-retention" for task in tasks), 5)
            self.assertEqual(sum(task["cohort"] == "repair" for task in tasks), 5)
            self.assertTrue(any(task["stratum"] == "integration" for task in tasks))
            for task in tasks:
                hidden = first / str(task["hidden_tests_path"])
                reference = first / str(task["reference_path"])
                self.assertEqual(tree_digest(hidden), task["hidden_tests_tree_sha256"])
                self.assertEqual(tree_digest(reference), task["reference_tree_sha256"])
                self.assertFalse((hidden / "policy.py").exists())

    def test_committed_manifest_matches_fresh_materialization(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            generated = Path(directory) / "corpus"
            _ = materialize_native_cleanup_effect_v5(generated)
            committed = ROOT / "examples/effect-experiment-native-v5/manifest.json"
            self.assertEqual(json.loads((generated / "manifest.json").read_text(encoding="utf-8")), json.loads(committed.read_text(encoding="utf-8")))

    def test_hidden_contract_rejects_initial_and_policy_only_repairs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            corpus = Path(directory) / "corpus"
            manifest = materialize_native_cleanup_effect_v5(corpus)
            for task in cast(list[dict[str, object]], manifest["tasks"]):
                task_id = str(task["task_id"])
                hidden = corpus / str(task["hidden_tests_path"]) / "tests/test_hidden.py"
                reference = corpus / str(task["reference_path"])
                with self.subTest(task=task_id, phase="reference"):
                    self.assertEqual(run_suite(reference).returncode, 0)
                with self.subTest(task=task_id, phase="initial"):
                    initial = Path(directory) / "initial" / task_id
                    initial.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copytree(corpus / str(task["workspace_path"]), initial)
                    _ = shutil.copy2(hidden, initial / "tests/test_hidden.py")
                    self.assertNotEqual(run_suite(initial).returncode, 0)
                with self.subTest(task=task_id, phase="policy-only"):
                    shallow = Path(directory) / "shallow" / task_id
                    shallow.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copytree(corpus / str(task["workspace_path"]), shallow)
                    _ = shutil.copy2(reference / "policy.py", shallow / "policy.py")
                    _ = shutil.copy2(hidden, shallow / "tests/test_hidden.py")
                    self.assertNotEqual(run_suite(shallow).returncode, 0)

    def test_dynamic_retention_and_unconsumed_wrapper_are_opposite_traps(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            corpus = Path(directory) / "corpus"
            manifest = materialize_native_cleanup_effect_v5(corpus)
            tasks = cast(list[dict[str, object]], manifest["tasks"])
            dynamic = next(task for task in tasks if task["kind"] == "dynamic_retain")
            semantic = next(task for task in tasks if task["kind"] == "semantic_duplicate")

            retained = Path(directory) / "retained"
            shutil.copytree(corpus / str(dynamic["reference_path"]), retained)
            adapter = retained / f"plugins/{dynamic['task_id']}_adapter.py"
            adapter.unlink()
            _ = shutil.copy2(corpus / str(dynamic["hidden_tests_path"]) / "tests/test_hidden.py", retained / "tests/test_hidden.py")
            self.assertNotEqual(run_suite(retained).returncode, 0)

            wrapper = Path(directory) / "wrapper"
            shutil.copytree(corpus / str(semantic["reference_path"]), wrapper)
            legacy = wrapper / "compat/legacy_wrapper.py"
            legacy.parent.mkdir(parents=True)
            _ = legacy.write_text("def normalize(value):\n    return value\n", encoding="utf-8")
            _ = shutil.copy2(corpus / str(semantic["hidden_tests_path"]) / "tests/test_hidden.py", wrapper / "tests/test_hidden.py")
            self.assertNotEqual(run_suite(wrapper).returncode, 0)

    def test_selected_task_order_is_a_distinct_v5_contract(self) -> None:
        self.assertEqual(len(TASKS), 10)
        self.assertEqual(len({task.task_id for task in TASKS}), len(TASKS))
        self.assertTrue(all(task.task_id.startswith("cleanup_v10_") for task in TASKS))
        self.assertTrue({task.task_id for task in TASKS}.isdisjoint(V4_TASK_IDS))


if __name__ == "__main__":
    _ = unittest.main()
