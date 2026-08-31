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
from materialize_native_cleanup_effect_v2 import TASKS, materialize_native_cleanup_effect_v2  # noqa: E402


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


class NativeCleanupEffectV2Tests(unittest.TestCase):
    def test_materialization_covers_each_cohort_and_stratum(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            corpus = Path(directory) / "corpus"
            manifest = materialize_native_cleanup_effect_v2(corpus)
            tasks = cast(list[dict[str, object]], manifest["tasks"])
            self.assertEqual(len(tasks), 10)
            self.assertEqual({task["cohort"] for task in tasks}, {"decision-retention", "repair"})
            for cohort in ("decision-retention", "repair"):
                selected = [task for task in tasks if task["cohort"] == cohort]
                self.assertEqual(len(selected), 5)
                self.assertEqual(
                    {task["stratum"] for task in selected},
                    {"single-module", "cross-module", "integration"},
                )
            for task in tasks:
                hidden = corpus / str(task["hidden_tests_path"])
                reference = corpus / str(task["reference_path"])
                workspace = corpus / str(task["workspace_path"])
                self.assertEqual(tree_digest(hidden), task["hidden_tests_tree_sha256"])
                self.assertEqual(tree_digest(reference), task["reference_tree_sha256"])
                self.assertFalse((hidden / "policy.py").exists())
                if task["stratum"] == "single-module":
                    self.assertFalse((workspace / "consumers").exists())
                    self.assertFalse((workspace / "plugins").exists())
                elif task["stratum"] == "cross-module":
                    self.assertTrue((workspace / f"consumers/{task['task_id']}_consumer.py").is_file())
                    self.assertFalse((workspace / "plugins").exists())
                else:
                    self.assertTrue((workspace / f"plugins/{task['task_id']}_adapter.py").is_file())
                    self.assertTrue((workspace / f"runtime/{task['task_id']}.json").is_file())

    def test_committed_manifest_matches_a_fresh_v2_materialization(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            corpus = Path(directory) / "corpus"
            _ = materialize_native_cleanup_effect_v2(corpus)
            committed = ROOT / "examples" / "effect-experiment-native-v2" / "manifest.json"
            self.assertEqual(
                json.loads((corpus / "manifest.json").read_text(encoding="utf-8")),
                json.loads(committed.read_text(encoding="utf-8")),
            )

    def test_hidden_contract_rejects_shallow_replacement_and_accepts_reference(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            corpus = Path(directory) / "corpus"
            manifest = materialize_native_cleanup_effect_v2(corpus)
            for task in cast(list[dict[str, object]], manifest["tasks"]):
                task_id = str(task["task_id"])
                workspace = corpus / str(task["workspace_path"])
                reference = corpus / str(task["reference_path"])
                hidden = corpus / str(task["hidden_tests_path"]) / "tests" / "test_hidden.py"
                with self.subTest(task=task_id, phase="reference"):
                    self.assertEqual(run_suite(reference).returncode, 0)
                with self.subTest(task=task_id, phase="policy-only"):
                    candidate = Path(directory) / "policy-only" / task_id
                    candidate.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copytree(workspace, candidate)
                    _ = shutil.copy2(reference / "policy.py", candidate / "policy.py")
                    _ = shutil.copy2(hidden, candidate / "tests" / "test_hidden.py")
                    self.assertNotEqual(run_suite(candidate).returncode, 0)

    def test_initial_public_contract_distinguishes_retention_from_repair(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            corpus = Path(directory) / "corpus"
            manifest = materialize_native_cleanup_effect_v2(corpus)
            for task in cast(list[dict[str, object]], manifest["tasks"]):
                workspace = corpus / str(task["workspace_path"])
                result = run_suite(workspace)
                with self.subTest(task=task["task_id"], cohort=task["cohort"]):
                    if task["cohort"] == "decision-retention":
                        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    else:
                        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_registry_retarget_and_adapter_deletion_fail_hidden_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            corpus = Path(directory) / "corpus"
            manifest = materialize_native_cleanup_effect_v2(corpus)
            task = next(item for item in cast(list[dict[str, object]], manifest["tasks"]) if item["stratum"] == "integration")
            task_id = str(task["task_id"])
            candidate = Path(directory) / "candidate"
            shutil.copytree(corpus / str(task["reference_path"]), candidate)
            policy = candidate / "policy.py"
            _ = policy.write_text(
                policy.read_text(encoding="utf-8")
                + "\n\ndef normalize(value):\n    return canonical_normalize(value)\n",
                encoding="utf-8",
            )
            (candidate / f"plugins/{task_id}_adapter.py").unlink()
            _ = (candidate / f"runtime/{task_id}.json").write_text(
                json.dumps({"adapter": "policy"}, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            _ = shutil.copy2(
                corpus / str(task["hidden_tests_path"]) / "tests" / "test_hidden.py",
                candidate / "tests" / "test_hidden.py",
            )
            result = run_suite(candidate)
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_hidden_contract_rejects_erased_current_descriptions_and_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            corpus = Path(directory) / "corpus"
            manifest = materialize_native_cleanup_effect_v2(corpus)
            task = cast(list[dict[str, object]], manifest["tasks"])[0]
            candidate = Path(directory) / "candidate"
            shutil.copytree(corpus / str(task["reference_path"]), candidate)
            for relative in ("README.md", f"docs/{task['task_id']}.md", "runbook.md", "package-metadata.json"):
                _ = (candidate / relative).write_text("", encoding="utf-8")
            _ = shutil.copy2(
                corpus / str(task["hidden_tests_path"]) / "tests" / "test_hidden.py",
                candidate / "tests" / "test_hidden.py",
            )
            result = run_suite(candidate)
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_consumers_must_delegate_to_canonical_policy_owner(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            corpus = Path(directory) / "corpus"
            manifest = materialize_native_cleanup_effect_v2(corpus)
            tasks = cast(list[dict[str, object]], manifest["tasks"])
            for stratum in ("cross-module", "integration"):
                task = next(item for item in tasks if item["stratum"] == stratum)
                candidate = Path(directory) / stratum
                shutil.copytree(corpus / str(task["reference_path"]), candidate)
                if stratum == "cross-module":
                    path = candidate / f"consumers/{task['task_id']}_consumer.py"
                    source = "from policy import evaluate\n\ndef request_value(value):\n    return '-'.join(value.strip().casefold().split())\n"
                else:
                    path = candidate / f"plugins/{task['task_id']}_adapter.py"
                    source = "from policy import canonical_normalize\n\ndef normalize(value):\n    return '-'.join(value.strip().casefold().split())\n"
                _ = path.write_text(source, encoding="utf-8")
                _ = shutil.copy2(
                    corpus / str(task["hidden_tests_path"]) / "tests" / "test_hidden.py",
                    candidate / "tests" / "test_hidden.py",
                )
                result = run_suite(candidate)
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    _ = unittest.main()
