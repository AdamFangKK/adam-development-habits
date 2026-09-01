from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import cast


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from analyze_native_cleanup_effect_v6 import replay_score, require_replay_match  # noqa: E402
from materialize_effect_corpus_v9 import tree_digest  # noqa: E402
from materialize_native_cleanup_effect_v6 import materialize_native_cleanup_effect_v6  # noqa: E402
from native_cleanup_effect_runner_v6 import (  # noqa: E402
    FINAL_ARTIFACTS,
    PREPARE_ARTIFACTS,
    mark_agent_complete,
    prepare_condition,
    score_condition,
)
from run_native_cleanup_effect_v6_api import build_agent_command, transcript_text  # noqa: E402


def preregistration_for(task_id: str, order: list[str]) -> dict[str, object]:
    return {"task_plan": {"tasks": [{"task_id": task_id, "execution_order": order}]}}


def complete_agent(raw: Path, task_id: str, condition: str, transcript: Path) -> None:
    _ = transcript.write_text("Native test agent completed the prepared workspace.\n", encoding="utf-8")
    mark_agent_complete(
        raw,
        task_id,
        condition,
        agent_id=f"/root/native-v6-test-{task_id}-{condition}",
        model_id="gpt-5.5",
        started_at="2026-08-31T20:00:00Z",
        finished_at="2026-08-31T20:00:01Z",
        transcript=transcript,
    )


def write_synthetic_corpus(root: Path, *, allowed_edit_paths: list[str]) -> tuple[Path, str]:
    corpus = root / "corpus"
    task_id = "synthetic_untracked_v6"
    workspace = corpus / "tasks" / task_id
    hidden = corpus / "hidden-tests" / task_id
    reference = corpus / "references" / task_id
    (workspace / "tests").mkdir(parents=True)
    (hidden / "tests").mkdir(parents=True)
    reference.mkdir(parents=True)
    _ = (workspace / "service.py").write_text("VALUE = 1\n", encoding="utf-8")
    _ = (workspace / "tests" / "test_public.py").write_text(
        "import unittest\nimport service\n\nclass Public(unittest.TestCase):\n    def test_value(self):\n        self.assertEqual(service.VALUE, 1)\n",
        encoding="utf-8",
    )
    _ = (hidden / "tests" / "test_hidden.py").write_text(
        "import unittest\nimport service\n\nclass Hidden(unittest.TestCase):\n    def test_value(self):\n        self.assertEqual(service.VALUE, 1)\n",
        encoding="utf-8",
    )
    manifest = {
        "schema_version": 1,
        "tasks": [
            {
                "task_id": task_id,
                "workspace_path": f"tasks/{task_id}",
                "hidden_tests_path": f"hidden-tests/{task_id}",
                "reference_path": f"references/{task_id}",
                "allowed_edit_paths": allowed_edit_paths,
                "workspace_tree_sha256": tree_digest(workspace),
                "hidden_tests_tree_sha256": tree_digest(hidden),
                "reference_tree_sha256": tree_digest(reference),
            }
        ],
    }
    (corpus / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return corpus, task_id


class NativeCleanupEffectRunnerV6Tests(unittest.TestCase):
    def test_api_key_executor_requires_disabled_skill_search_and_records_it(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            corpus = root / "corpus"
            manifest = materialize_native_cleanup_effect_v6(corpus)
            task_id = cast(str, cast(list[dict[str, object]], manifest["tasks"])[0]["task_id"])
            preregistration = root / "preregistration.json"
            preregistration.write_text(json.dumps(preregistration_for(task_id, ["no_skill", "old_skill", "new_skill"])), encoding="utf-8")
            raw = root / "raw"
            workspace = root / "workspace"
            _ = prepare_condition(corpus, preregistration, ROOT, raw, task_id, "no_skill", workspace)
            transcript = root / "agent-output.md"
            transcript.write_text("agent finished\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "requires api-key mode"):
                mark_agent_complete(
                    raw,
                    task_id,
                    "no_skill",
                    agent_id="codex-cli:synthetic/no_skill",
                    model_id="gpt-5.5",
                    started_at="2026-08-31T20:00:00Z",
                    finished_at="2026-08-31T20:00:01Z",
                    transcript=transcript,
                    executor_kind="codex-cli-api-key",
                )
            mark_agent_complete(
                raw,
                task_id,
                "no_skill",
                agent_id="codex-cli:synthetic/no_skill",
                model_id="gpt-5.5",
                started_at="2026-08-31T20:00:00Z",
                finished_at="2026-08-31T20:00:01Z",
                transcript=transcript,
                executor_kind="codex-cli-api-key",
                auth_mode="api-key",
                skill_search_disabled=True,
                codex_cli_version="codex-cli 0.149.0-alpha.4.1",
            )
            agent = json.loads((raw / task_id / "no_skill" / "agent-result.json").read_text(encoding="utf-8"))
            executor = cast(dict[str, object], agent["executor"])
            self.assertEqual(executor["kind"], "codex-cli-api-key")
            self.assertTrue(executor["skill_search_disabled"])

    def test_api_command_disables_skill_search_and_redacts_a_key_from_transcript(self) -> None:
        command = build_agent_command(
            codex="/usr/local/bin/codex",
            workspace=Path("/tmp/v6-workspace"),
            model="gpt-5.5",
            prompt="Fix the visible task only.",
        )
        self.assertEqual(command[:4], ["/usr/local/bin/codex", "exec", "--disable", "skill_search"])
        self.assertIn("--ignore-user-config", command)
        self.assertIn("workspace-write", command)
        self.assertNotIn("frozen-policy.md", command)
        transcript = transcript_text(exit_code=0, stdout="sk-test-token", stderr="")
        self.assertNotIn("sk-test-token", transcript)
        self.assertIn("[REDACTED_API_KEY]", transcript)

    def test_later_condition_cannot_be_prepared_until_predecessor_is_scored(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            corpus = root / "corpus"
            manifest = materialize_native_cleanup_effect_v6(corpus)
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
            manifest = materialize_native_cleanup_effect_v6(corpus)
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

    def test_untracked_allowed_file_is_captured_before_scoring_and_replayable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            corpus, task_id = write_synthetic_corpus(root, allowed_edit_paths=["notes/new_contract.md"])
            preregistration = root / "preregistration.json"
            preregistration.write_text(json.dumps(preregistration_for(task_id, ["no_skill", "old_skill", "new_skill"])), encoding="utf-8")
            raw = root / "raw"
            workspace = root / "workspace"
            _ = prepare_condition(corpus, preregistration, ROOT, raw, task_id, "no_skill", workspace)
            (workspace / "notes").mkdir()
            _ = (workspace / "notes" / "new_contract.md").write_text("new allowed documentation\n", encoding="utf-8")
            complete_agent(raw, task_id, "no_skill", root / "agent-output.md")
            score = score_condition(corpus, raw, task_id, "no_skill", workspace)
            self.assertEqual(score["changed_paths"], ["notes/new_contract.md"])
            self.assertEqual(score["disallowed_changed_paths"], [])
            self.assertTrue(score["implementation_integrity_passed"])
            self.assertTrue(score["hidden_injected_after_agent_exit"])
            candidate_diff = raw / task_id / "no_skill" / "candidate.diff"
            self.assertIn("diff --git a/notes/new_contract.md b/notes/new_contract.md", candidate_diff.read_text(encoding="utf-8"))
            replayed = replay_score(corpus, task_id=task_id, condition="no_skill", candidate_diff=candidate_diff, root=ROOT)
            require_replay_match(cast(dict[str, object], score), replayed)

    def test_untracked_disallowed_file_is_captured_before_scoring_and_replayable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            corpus, task_id = write_synthetic_corpus(root, allowed_edit_paths=["service.py"])
            preregistration = root / "preregistration.json"
            preregistration.write_text(json.dumps(preregistration_for(task_id, ["no_skill", "old_skill", "new_skill"])), encoding="utf-8")
            raw = root / "raw"
            workspace = root / "workspace"
            _ = prepare_condition(corpus, preregistration, ROOT, raw, task_id, "no_skill", workspace)
            (workspace / "tmp").mkdir()
            _ = (workspace / "tmp" / "debug.txt").write_text("debug artifact\n", encoding="utf-8")
            complete_agent(raw, task_id, "no_skill", root / "agent-output.md")
            score = score_condition(corpus, raw, task_id, "no_skill", workspace)
            self.assertEqual(score["changed_paths"], ["tmp/debug.txt"])
            self.assertEqual(score["disallowed_changed_paths"], ["tmp/debug.txt"])
            self.assertFalse(score["implementation_integrity_passed"])
            self.assertFalse(score["hidden_injected_after_agent_exit"])
            candidate_diff = raw / task_id / "no_skill" / "candidate.diff"
            self.assertIn("diff --git a/tmp/debug.txt b/tmp/debug.txt", candidate_diff.read_text(encoding="utf-8"))
            replayed = replay_score(corpus, task_id=task_id, condition="no_skill", candidate_diff=candidate_diff, root=ROOT)
            require_replay_match(cast(dict[str, object], score), replayed)

    def test_preparation_refuses_wrong_condition_or_existing_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            corpus = root / "corpus"
            manifest = materialize_native_cleanup_effect_v6(corpus)
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
