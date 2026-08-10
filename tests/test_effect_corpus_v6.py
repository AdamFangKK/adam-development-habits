from __future__ import annotations

# The corpus generator is an intentionally standalone script without stubs.
# pyright: reportMissingTypeStubs=false

import json
import os
import subprocess
import sys
import tempfile
import unittest
import hashlib
from pathlib import Path
from typing import cast

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from analyze_skill_effect import analyze_experiment  # noqa: E402
from materialize_effect_corpus_v6 import make_tasks, tree_digest, write_tree  # noqa: E402


CORPUS = ROOT / "examples" / "effect-corpus-v6"
PREREGISTRATION = ROOT / "examples" / "effect-experiment-v6" / "preregistration.json"
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


class EffectCorpusV6Tests(unittest.TestCase):
    def test_preregistration_freezes_the_v6_envelope_before_collection(self) -> None:
        preregistration = cast(dict[str, object], json.loads(PREREGISTRATION.read_text(encoding="utf-8")))
        protocol = cast(dict[str, object], preregistration["protocol"])
        expected_hashes = {
            "corpus_manifest_sha256": CORPUS / "manifest.json",
            "generator_sha256": ROOT / "scripts" / "materialize_effect_corpus_v6.py",
            "runner_sha256": ROOT / "scripts" / "run_effect_experiment_v6.py",
            "hidden_scorer_sha256": ROOT / "scripts" / "score_effect_workspace_v6.py",
            "baseline_prompt_sha256": ROOT / "examples" / "effect-experiment-v6" / "prompts" / "baseline.txt",
            "skill_prompt_sha256": ROOT / "examples" / "effect-experiment-v6" / "prompts" / "skill.txt",
        }
        for field, path in expected_hashes.items():
            with self.subTest(field=field):
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), protocol[field])
        scope = cast(dict[str, object], preregistration["scope"])
        self.assertEqual(hashlib.sha256((ROOT / "SKILL.md").read_bytes()).hexdigest(), scope["skill_revision_sha256"])
        planned_tasks = cast(list[dict[str, object]], cast(dict[str, object], preregistration["task_plan"])["tasks"])
        manifest_tasks = cast(list[dict[str, object]], cast(dict[str, object], json.loads((CORPUS / "manifest.json").read_text(encoding="utf-8")))["tasks"])
        self.assertEqual(planned_tasks, [{"task_id": task["task_id"], "stratum": task["stratum"]} for task in manifest_tasks])
        report = analyze_experiment(preregistration)
        self.assertEqual(report["status"], "planned")
        self.assertEqual(report["conclusion"].split(":", 1)[0], "not_run")

    def test_manifest_is_fresh_multi_file_and_hash_linked(self) -> None:
        manifest = cast(dict[str, object], json.loads((CORPUS / "manifest.json").read_text(encoding="utf-8")))
        tasks = cast(list[dict[str, object]], manifest["tasks"])
        self.assertEqual(len(tasks), 20)
        self.assertEqual({str(task["stratum"]) for task in tasks}, {"single-module", "cross-module", "integration"})
        self.assertTrue(cast(dict[str, object], manifest["split"])["hidden_tests_are_injected_after_agent_exit"])
        for task in tasks:
            workspace = CORPUS / str(task["workspace_path"])
            hidden = CORPUS / str(task["hidden_root_path"])
            self.assertTrue(workspace.is_dir())
            self.assertTrue(hidden.is_dir())
            self.assertEqual(tree_digest(workspace), task["workspace_tree_sha256"])
            self.assertEqual(tree_digest(hidden), task["hidden_tree_sha256"])
            self.assertFalse((workspace / "tests" / "test_hidden.py").exists())
            self.assertTrue(set(cast(list[str], task["allowed_edit_paths"])).isdisjoint({"task.md", "tests/test_public.py"}))

    def test_every_buggy_fixture_fails_public_and_fixed_fixture_passes_hidden(self) -> None:
        manifest = cast(dict[str, object], json.loads((CORPUS / "manifest.json").read_text(encoding="utf-8")))
        tasks_by_id = {task.task_id: task for task in make_tasks()}
        records = cast(list[dict[str, object]], manifest["tasks"])
        with tempfile.TemporaryDirectory(prefix="adam-effect-v6-corpus-test-") as directory:
            root = Path(directory)
            for record in records:
                task_id = str(record["task_id"])
                task = tasks_by_id[task_id]
                buggy_root = CORPUS / str(record["workspace_path"])
                public = run_suite(buggy_root)
                self.assertNotEqual(public.returncode, 0, task_id + " unexpectedly passes public tests")

                fixed_root = root / task_id
                write_tree(fixed_root, task.fixed | {"task.md": task.description, "tests/test_public.py": task.public_test, "tests/test_hidden.py": task.hidden_test})
                hidden = run_suite(fixed_root)
                self.assertEqual(hidden.returncode, 0, f"{task_id}:\n{hidden.stdout}\n{hidden.stderr}")


if __name__ == "__main__":
    _ = unittest.main()
