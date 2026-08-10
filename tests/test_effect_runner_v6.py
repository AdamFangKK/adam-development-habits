from __future__ import annotations

# The scripts are intentionally standalone modules without package stubs.
# pyright: reportMissingTypeStubs=false

import sys
import tempfile
import unittest
import json
from pathlib import Path
from typing import cast
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from analyze_skill_effect import skill_first_for  # noqa: E402
from run_effect_experiment_v6 import (  # noqa: E402
    Arguments,
    TaskRecord,
    changed_paths,
    execute_task_pair,
    records_for_preregistration,
    seed_workspace,
    main,
)
from score_effect_workspace_v6 import score_workspace  # noqa: E402


class EffectRunnerV6Tests(unittest.TestCase):
    def test_seed_workspace_copies_a_multi_file_public_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            source.mkdir()
            _ = (source / "service.py").write_text("value = 1\n", encoding="utf-8")
            tests = source / "tests"
            tests.mkdir()
            _ = (tests / "test_public.py").write_text("import service\nassert service.value == 1\n", encoding="utf-8")
            run = root / "run"
            seed = seed_workspace(source, run)
            self.assertTrue((run / "service.py").is_file())
            self.assertTrue((run / "tests" / "test_public.py").is_file())
            _ = (run / "service.py").write_text("value = 2\n", encoding="utf-8")
            self.assertEqual(changed_paths(run, seed), ["service.py"])

    def test_hidden_scorer_injects_only_into_a_temporary_copy(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = root / "workspace"
            workspace.mkdir()
            _ = (workspace / "calculator.py").write_text("def total(left, right):\n    return left + right\n", encoding="utf-8")
            hidden = root / "hidden"
            tests = hidden / "tests"
            tests.mkdir(parents=True)
            _ = (tests / "test_hidden.py").write_text(
                "import unittest\nfrom calculator import total\n\nclass Hidden(unittest.TestCase):\n    def test_total(self):\n        self.assertEqual(total(20, 22), 42)\n",
                encoding="utf-8",
            )
            report = score_workspace(
                workspace,
                hidden,
                [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
                timeout=5.0,
            )
            self.assertTrue(report["passed"], report)
            self.assertFalse((workspace / "tests").exists())

    def test_task_pair_preserves_preregistered_order(self) -> None:
        task = TaskRecord(
            task_id="order-check",
            stratum="cross-module",
            workspace_path="tasks/order-check",
            hidden_root_path="hidden/order-check",
            allowed_edit_paths=("service.py",),
            public_command=(sys.executable, "-m", "unittest"),
            hidden_command=(sys.executable, "-m", "unittest"),
        )
        arguments = Arguments(
            corpus=Path("/tmp/corpus"),
            prompts=Path("/tmp/prompts"),
            skill=Path("/tmp/skill/SKILL.md"),
            preregistration=Path("/tmp/preregistration.json"),
            preregistration_commit="a" * 40,
            raw_output=Path("/tmp/raw"),
            output=Path("/tmp/out.json"),
            seed=11,
            codex="codex",
            model="model",
            harness="harness",
            agent_timeout=1.0,
            test_timeout=1.0,
        )
        expected = ("skill", "baseline") if skill_first_for(arguments.seed, task.task_id, 1) else ("baseline", "skill")
        calls: list[str] = []

        def fake_execute_condition(**kwargs: object) -> dict[str, object]:
            condition = str(kwargs["condition"])
            calls.append(condition)
            return {"condition": condition, "trial_complete": True, "hidden_repair_pass": True, "scope_ok": True}

        with patch("run_effect_experiment_v6.execute_condition", side_effect=fake_execute_condition):
            results = execute_task_pair(
                task=task,
                corpus=arguments.corpus,
                prompts=arguments.prompts,
                skill_snapshot=Path("/tmp/skill/SKILL.md"),
                raw_root=arguments.raw_output,
                arguments=arguments,
            )
        self.assertEqual(tuple(calls), expected)
        self.assertEqual([result["execution_order"] for result in results], [1, 2])
        self.assertEqual({result["pair_id"] for result in results}, {"order-check-run-1"})

    def test_preregistration_must_cover_manifest_once(self) -> None:
        corpus = cast(dict[str, object], {
            "tasks": [
                {
                    "task_id": "one",
                    "stratum": "single-module",
                    "workspace_path": "tasks/one",
                    "hidden_root_path": "hidden/one",
                    "allowed_edit_paths": ["owner.py"],
                    "public_command": ["python3", "-m", "unittest"],
                    "hidden_command": ["python3", "-m", "unittest"],
                }
            ]
        })
        preregistration = cast(dict[str, object], {"task_plan": {"tasks": [{"task_id": "one", "stratum": "single-module"}]}})
        self.assertEqual([record.task_id for record in records_for_preregistration(corpus, preregistration)], ["one"])
        with self.assertRaisesRegex(ValueError, "every corpus task"):
            _ = records_for_preregistration(corpus, {"task_plan": {"tasks": []}})

    def test_main_checkpoints_completed_and_interrupted_pairs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            corpus = root / "corpus"
            corpus.mkdir()
            _ = (corpus / "manifest.json").write_text(json.dumps({"tasks": [{
                "task_id": "one",
                "stratum": "single-module",
                "workspace_path": "tasks/one",
                "hidden_root_path": "hidden/one",
                "allowed_edit_paths": ["owner.py"],
                "public_command": [sys.executable, "-m", "unittest"],
                "hidden_command": [sys.executable, "-m", "unittest"],
            }]}), encoding="utf-8")
            prompts = root / "prompts"
            prompts.mkdir()
            _ = (prompts / "baseline.txt").write_text("baseline", encoding="utf-8")
            _ = (prompts / "skill.txt").write_text("skill", encoding="utf-8")
            skill = root / "SKILL.md"
            _ = skill.write_text("# skill\n", encoding="utf-8")
            preregistration = root / "preregistration.json"
            _ = preregistration.write_text(json.dumps({
                "schema_version": 1,
                "status": "planned",
                "trials": [],
                "scope": {"model_id": "model", "harness_id": "harness"},
                "preregistration": {},
                "task_plan": {"tasks": [{"task_id": "one", "stratum": "single-module"}]},
            }), encoding="utf-8")

            def invoke(result: list[dict[str, object]], output: Path) -> int:
                with patch("run_effect_experiment_v6.execute_task_pair", return_value=result), patch.object(sys, "argv", [
                    "runner",
                    "--corpus", str(corpus),
                    "--prompts", str(prompts),
                    "--skill", str(skill),
                    "--preregistration", str(preregistration),
                    "--preregistration-commit", "a" * 40,
                    "--raw-output", str(root / "raw"),
                    "--output", str(output),
                    "--seed", "1",
                    "--model", "model",
                    "--harness", "harness",
                ]):
                    return main()

            complete = cast(list[dict[str, object]], [
                {"task_id": "one", "condition": "baseline", "trial_complete": True, "hidden_repair_pass": False, "scope_ok": True},
                {"task_id": "one", "condition": "skill", "trial_complete": True, "hidden_repair_pass": True, "scope_ok": True},
            ])
            completed_output = root / "completed.json"
            self.assertEqual(invoke(complete, completed_output), 0)
            completed = cast(dict[str, object], json.loads(completed_output.read_text(encoding="utf-8")))
            self.assertEqual(completed["status"], "completed")
            self.assertEqual(len(cast(list[object], completed["trials"])), 2)
            self.assertEqual(cast(dict[str, object], completed["preregistration"])["git_commit"], "a" * 40)

            interrupted = cast(list[dict[str, object]], [
                {"task_id": "one", "condition": "baseline", "trial_complete": False, "hidden_repair_pass": False, "scope_ok": True},
                {"task_id": "one", "condition": "skill", "trial_complete": True, "hidden_repair_pass": True, "scope_ok": True},
            ])
            interrupted_output = root / "interrupted.json"
            self.assertEqual(invoke(interrupted, interrupted_output), 2)
            saved = cast(dict[str, object], json.loads(interrupted_output.read_text(encoding="utf-8")))
            self.assertEqual(saved["status"], "interrupted")
            self.assertIn("no retry", cast(str, cast(dict[str, object], saved["collection"])["ineligible_reason"]))


if __name__ == "__main__":
    _ = unittest.main()
