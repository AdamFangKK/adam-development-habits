from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import cast


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from materialize_native_cleanup_effect_v5 import materialize_native_cleanup_effect_v5  # noqa: E402
from native_cleanup_effect_runner_v5 import (  # noqa: E402
    FINAL_ARTIFACTS,
    PREPARE_ARTIFACTS,
    mark_agent_complete,
    prepare_condition,
    score_condition,
)


def preregistration_for(task_id: str, order: list[str]) -> dict[str, object]:
    return {"task_plan": {"tasks": [{"task_id": task_id, "execution_order": order}]}}


def complete_agent(raw: Path, task_id: str, condition: str, transcript: Path) -> None:
    _ = transcript.write_text("Native test agent completed the prepared workspace.\n", encoding="utf-8")
    mark_agent_complete(
        raw,
        task_id,
        condition,
        agent_id=f"/root/native-v5-test-{task_id}-{condition}",
        model_id="gpt-5.5",
        started_at="2026-08-31T20:00:00Z",
        finished_at="2026-08-31T20:00:01Z",
        transcript=transcript,
    )


class NativeCleanupEffectRunnerV5Tests(unittest.TestCase):
    def test_later_condition_cannot_be_prepared_until_predecessor_is_scored(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            corpus = root / "corpus"
            manifest = materialize_native_cleanup_effect_v5(corpus)
            task = cast(list[dict[str, object]], manifest["tasks"])[0]
            task_id = cast(str, task["task_id"])
            preregistration = root / "preregistration.json"
            order = ["old_skill", "new_skill", "no_skill"]
            preregistration.write_text(json.dumps(preregistration_for(task_id, order)), encoding="utf-8")
            raw = root / "raw"
            first_workspace = root / "workspaces" / "old"
            prepared = prepare_condition(corpus, preregistration, ROOT, raw, task_id, "old_skill", first_workspace)
            self.assertEqual(prepared.condition, "old_skill")
            self.assertEqual({path.name for path in (raw / task_id / "old_skill").iterdir()}, PREPARE_ARTIFACTS)
            self.assertTrue((first_workspace / "frozen-policy.md").is_file())
            with self.assertRaisesRegex(ValueError, "incomplete or unexpected artifacts"):
                _ = prepare_condition(corpus, preregistration, ROOT, raw, task_id, "new_skill", root / "workspaces" / "new")

            complete_agent(raw, task_id, "old_skill", root / "agent-output.md")
            score = score_condition(corpus, raw, task_id, "old_skill", first_workspace)
            self.assertTrue(score["hidden_injected_after_agent_exit"])
            self.assertTrue(score["scored_after_agent_exit"])
            provenance = cast(dict[str, object], score["scorer_provenance"])
            self.assertEqual(provenance["base_runner_path"], "scripts/native_cleanup_effect_runner_v1.py")
            self.assertEqual(provenance["corpus_manifest_sha256"], __import__("hashlib").sha256((corpus / "manifest.json").read_bytes()).hexdigest())
            self.assertEqual(
                set(cast(dict[str, str], score["pre_score_artifact_sha256"])),
                {"sequence.json", "prepare.json", "seed.txt", "agent-prompt.txt", "agent-transcript.md", "agent-result.json", "candidate.diff"},
            )
            self.assertEqual({path.name for path in (raw / task_id / "old_skill").iterdir()}, FINAL_ARTIFACTS)

            second_workspace = root / "workspaces" / "new"
            prepared = prepare_condition(corpus, preregistration, ROOT, raw, task_id, "new_skill", second_workspace)
            self.assertEqual(prepared.condition, "new_skill")
            sequence = json.loads((raw / task_id / "new_skill" / "sequence.json").read_text(encoding="utf-8"))
            self.assertEqual(sequence["predecessor_score_sha256"][0]["condition"], "old_skill")
            self.assertEqual(len(sequence["predecessor_score_sha256"][0]["sha256"]), 64)

    def test_scored_integrity_failure_remains_a_valid_predecessor(self) -> None:
        """A failed sample must not erase the paired conditions that follow it."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            corpus = root / "corpus"
            manifest = materialize_native_cleanup_effect_v5(corpus)
            task_id = cast(str, cast(list[dict[str, object]], manifest["tasks"])[0]["task_id"])
            preregistration = root / "preregistration.json"
            order = ["old_skill", "new_skill", "no_skill"]
            preregistration.write_text(json.dumps(preregistration_for(task_id, order)), encoding="utf-8")
            raw = root / "raw"
            first_workspace = root / "workspaces" / "old"
            _ = prepare_condition(corpus, preregistration, ROOT, raw, task_id, "old_skill", first_workspace)
            _ = (first_workspace / "outside-allowed-surface.txt").write_text("unexpected\n", encoding="utf-8")
            complete_agent(raw, task_id, "old_skill", root / "agent-output.md")
            score = score_condition(corpus, raw, task_id, "old_skill", first_workspace)
            self.assertFalse(score["implementation_integrity_passed"])
            self.assertFalse(score["hidden_injected_after_agent_exit"])
            self.assertTrue(score["scored_after_agent_exit"])

            second_workspace = root / "workspaces" / "new"
            prepared = prepare_condition(corpus, preregistration, ROOT, raw, task_id, "new_skill", second_workspace)
            self.assertEqual(prepared.condition, "new_skill")

    def test_preparation_refuses_wrong_condition_or_existing_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            corpus = root / "corpus"
            manifest = materialize_native_cleanup_effect_v5(corpus)
            task_id = cast(str, cast(list[dict[str, object]], manifest["tasks"])[0]["task_id"])
            preregistration = root / "preregistration.json"
            preregistration.write_text(json.dumps(preregistration_for(task_id, ["no_skill", "old_skill", "new_skill"])), encoding="utf-8")
            workspace = root / "workspace"
            workspace.mkdir()
            with self.assertRaises(FileExistsError):
                _ = prepare_condition(corpus, preregistration, ROOT, root / "raw", task_id, "no_skill", workspace)
            with self.assertRaises(KeyError):
                _ = prepare_condition(corpus, preregistration, ROOT, root / "raw", "unknown", "no_skill", root / "other")


if __name__ == "__main__":
    _ = unittest.main()
