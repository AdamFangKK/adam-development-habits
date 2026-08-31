from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from typing import cast


ROOT = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(ROOT / "scripts"))

from materialize_native_cleanup_effect_v2 import materialize_native_cleanup_effect_v2  # noqa: E402
from native_cleanup_effect_runner_v1 import prepare_trial, score_trial  # noqa: E402


class NativeCleanupEffectRunnerV2Tests(unittest.TestCase):
    def test_preparation_exposes_only_public_task_tree_and_scoring_accepts_reference(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            private_corpus = root / "private-corpus"
            public_root = root / "agent-visible" / "trial"
            manifest = materialize_native_cleanup_effect_v2(private_corpus)
            task = cast(list[dict[str, object]], manifest["tasks"])[0]
            prepared = prepare_trial(private_corpus, str(task["task_id"]), public_root)

            self.assertTrue((public_root / "task.md").is_file())
            self.assertFalse((public_root / "references").exists())
            self.assertFalse((public_root / "hidden-tests").exists())
            self.assertNotIn(private_corpus, public_root.parents)

            reference = private_corpus / str(task["reference_path"])
            for item in reference.iterdir():
                if item.name in {"task.md", "tests"}:
                    continue
                destination = public_root / item.name
                if item.is_dir():
                    shutil.rmtree(destination, ignore_errors=True)
                    shutil.copytree(item, destination)
                else:
                    _ = shutil.copy2(item, destination)
            legacy = public_root / f"legacy/{task['task_id']}.py"
            legacy.unlink()
            result = score_trial(private_corpus, str(task["task_id"]), public_root, prepared.seed_commit)
            self.assertTrue(result["implementation_integrity_passed"])
            self.assertTrue(result["hidden_repair_passed"])
            self.assertTrue(result["hidden_injected_after_agent_exit"])

    def test_scoring_rejects_public_test_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            private_corpus = root / "private-corpus"
            public_root = root / "agent-visible" / "trial"
            manifest = materialize_native_cleanup_effect_v2(private_corpus)
            task = cast(list[dict[str, object]], manifest["tasks"])[0]
            prepared = prepare_trial(private_corpus, str(task["task_id"]), public_root)
            _ = (public_root / "tests/test_public.py").write_text("# mutated\n", encoding="utf-8")
            result = score_trial(private_corpus, str(task["task_id"]), public_root, prepared.seed_commit)
            self.assertFalse(result["implementation_integrity_passed"])
            self.assertIn("tests/test_public.py", result["disallowed_changed_paths"])

    def test_score_result_is_machine_readable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            private_corpus = root / "private-corpus"
            public_root = root / "agent-visible" / "trial"
            manifest = materialize_native_cleanup_effect_v2(private_corpus)
            task = cast(list[dict[str, object]], manifest["tasks"])[0]
            prepared = prepare_trial(private_corpus, str(task["task_id"]), public_root)
            result = score_trial(private_corpus, str(task["task_id"]), public_root, prepared.seed_commit)
            rendered = json.dumps(result, sort_keys=True)
            self.assertIn('"hidden_injected_after_agent_exit": true', rendered)


if __name__ == "__main__":
    _ = unittest.main()
