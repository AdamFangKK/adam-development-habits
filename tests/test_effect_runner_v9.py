from __future__ import annotations

import json
import hashlib
import subprocess
import sys
import tempfile
import unittest
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import cast
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import codex_v9_isolated as wrapper  # noqa: E402
from analyze_skill_effect_v9 import balanced_condition_order  # noqa: E402
from run_effect_experiment_v9 import (  # noqa: E402
    Arguments,
    TaskRecord,
    execute_condition,
    execute_task_block,
    main,
    records_for_preregistration,
    validate_frozen_worktree,
)


class EffectRunnerV9Tests(unittest.TestCase):
    def test_frozen_worktree_requires_tracked_inputs_and_preregistration_only_second_commit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()

            def git(*arguments: str) -> str:
                result = subprocess.run(["git", *arguments], cwd=root, capture_output=True, text=True, check=True)
                return result.stdout.strip()

            git("init", "-q")
            git("config", "user.email", "v9-test@example.invalid")
            git("config", "user.name", "V9 Test")
            corpus = root / "corpus"
            prompts = root / "prompts"
            old_skill = root / "skills" / "old" / "SKILL.md"
            new_skill = root / "skills" / "new" / "SKILL.md"
            corpus.mkdir()
            prompts.mkdir()
            old_skill.parent.mkdir(parents=True)
            new_skill.parent.mkdir(parents=True)
            _ = (corpus / "manifest.json").write_text("{}\n", encoding="utf-8")
            for name in ("no_skill.txt", "old_skill.txt", "new_skill.txt"):
                _ = (prompts / name).write_text(name + "\n", encoding="utf-8")
            _ = old_skill.write_text("old\n", encoding="utf-8")
            _ = new_skill.write_text("new\n", encoding="utf-8")
            protocol_files = []
            for name in ("runner.py", "scorer.py"):
                path = root / "scripts" / name
                path.parent.mkdir(exist_ok=True)
                _ = path.write_text(name + "\n", encoding="utf-8")
                protocol_files.append(path)
            git("add", ".")
            git("commit", "-qm", "freeze inputs")
            input_commit = git("rev-parse", "HEAD")
            preregistration = root / "experiment" / "preregistration.json"
            preregistration.parent.mkdir()
            payload = {"preregistration": {"git_commit": input_commit}}
            _ = preregistration.write_text(json.dumps(payload) + "\n", encoding="utf-8")
            git("add", str(preregistration.relative_to(root)))
            git("commit", "-qm", "freeze preregistration")
            head = git("rev-parse", "HEAD")
            arguments = Arguments(
                corpus=corpus,
                prompts=prompts,
                old_skill=old_skill,
                new_skill=new_skill,
                preregistration=preregistration,
                preregistration_commit=head,
                raw_output=root.parent / "unused-v9-raw",
                output=root.parent / "unused-v9-result.json",
                seed=1,
                codex="codex",
                model="model",
                harness="harness",
                agent_timeout=1.0,
                test_timeout=1.0,
                preflight=True,
            )
            with patch("run_effect_experiment_v9.frozen_protocol_files", return_value=tuple(protocol_files)):
                self.assertEqual(validate_frozen_worktree(arguments, payload), root)
                _ = (prompts / "no_skill.txt").write_text("drift\n", encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "clean Git worktree"):
                    _ = validate_frozen_worktree(arguments, payload)

    def test_wrapper_injects_skill_search_disable_once(self) -> None:
        self.assertTrue(Path(wrapper.__file__).resolve().stat().st_mode & 0o111)
        self.assertEqual(
            wrapper.inject_skill_search_disable(["exec", "-C", "/tmp/work", "prompt"]),
            ["exec", "--disable", "skill_search", "-C", "/tmp/work", "prompt"],
        )
        self.assertEqual(
            wrapper.inject_skill_search_disable(["exec", "--disable", "skill_search", "prompt"]),
            ["exec", "--disable", "skill_search", "prompt"],
        )

    def test_execute_condition_records_skill_snapshot_and_hidden_integrity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            corpus = root / "corpus"
            task_root = corpus / "tasks" / "smoke"
            hidden_root = corpus / "hidden-tests" / "smoke" / "tests"
            (task_root / "tests").mkdir(parents=True)
            hidden_root.mkdir(parents=True)
            _ = (task_root / "policy.py").write_text("def evaluate():\n    return 1\n", encoding="utf-8")
            _ = (task_root / "task.md").write_text("Return 1.\n", encoding="utf-8")
            _ = (task_root / "tests" / "test_public.py").write_text(
                "import unittest\nfrom policy import evaluate\n\nclass Public(unittest.TestCase):\n    def test_value(self):\n        self.assertEqual(evaluate(), 1)\n",
                encoding="utf-8",
            )
            _ = (hidden_root / "test_hidden.py").write_text(
                "import unittest\nfrom policy import evaluate\n\nclass Hidden(unittest.TestCase):\n    def test_value(self):\n        self.assertEqual(evaluate(), 1)\n",
                encoding="utf-8",
            )
            prompts = root / "prompts"
            prompts.mkdir()
            _ = (prompts / "new_skill.txt").write_text("Use {skill_path}", encoding="utf-8")
            skill = root / "skill" / "SKILL.md"
            skill.parent.mkdir()
            _ = skill.write_text("# Skill\n", encoding="utf-8")
            skill_text = skill.read_text(encoding="utf-8")
            task = TaskRecord(
                task_id="smoke",
                cohort="repair",
                stratum="single-module",
                workspace_path="tasks/smoke",
                hidden_tests_path="hidden-tests/smoke",
                allowed_edit_paths=("policy.py",),
                public_command=(sys.executable, "-m", "unittest", "discover", "-s", "tests"),
                hidden_command=(sys.executable, "-m", "unittest", "discover", "-s", "tests"),
            )
            command_event = json.dumps({
                "type": "item.completed",
                "item": {
                    "type": "command_execution",
                    "command": f"cat {skill}",
                    "exit_code": 0,
                    "status": "completed",
                    "aggregated_output": skill_text,
                },
            }) + "\n"
            with patch("run_effect_experiment_v9.run_agent", return_value=(0, command_event, "V9 isolation wrapper: --disable skill_search\n")):
                result = execute_condition(
                    task=task,
                    corpus=corpus,
                    prompts=prompts,
                    condition="new_skill",
                    skill_snapshots={"new_skill": skill},
                    raw_root=root / "raw",
                    codex_path="unused",
                    model_id="model",
                    harness_id="harness",
                    agent_timeout=1.0,
                    test_timeout=5.0,
                )
            self.assertTrue(result["trial_complete"], result)
            self.assertTrue(result["hidden_repair_pass"], result)
            self.assertTrue(result["implementation_integrity_passed"], result)
            stderr = (root / "raw" / "smoke" / "new_skill" / "agent.stderr.log").read_text(encoding="utf-8")
            self.assertNotIn("The supplied Skill path is:", stderr)

    def test_task_block_uses_preregistered_three_condition_order(self) -> None:
        order = balanced_condition_order(11, 0)
        task = TaskRecord(
            task_id="order-check",
            cohort="decision-retention",
            stratum="cross-module",
            workspace_path="tasks/order-check",
            hidden_tests_path="hidden-tests/order-check",
            allowed_edit_paths=("policy.py",),
            public_command=(sys.executable, "-m", "unittest"),
            hidden_command=(sys.executable, "-m", "unittest"),
            execution_order=order,
        )
        arguments = Arguments(
            corpus=Path("/tmp/corpus"),
            prompts=Path("/tmp/prompts"),
            old_skill=Path("/tmp/old/SKILL.md"),
            new_skill=Path("/tmp/new/SKILL.md"),
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
            preflight=False,
        )
        calls: list[str] = []

        def fake_execute_condition(**kwargs: object) -> dict[str, object]:
            condition = cast(str, kwargs["condition"])
            calls.append(condition)
            return {"condition": condition, "trial_complete": True, "hidden_repair_pass": True, "scope_ok": True}

        with patch("run_effect_experiment_v9.execute_condition", side_effect=fake_execute_condition):
            results = execute_task_block(
                task=task,
                corpus=arguments.corpus,
                prompts=arguments.prompts,
                skill_snapshots={},
                raw_root=arguments.raw_output,
                arguments=arguments,
            )
        self.assertEqual(tuple(calls), order)
        self.assertEqual([result["execution_order"] for result in results], [1, 2, 3])
        self.assertEqual({result["block_id"] for result in results}, {"order-check-run-1"})

    def test_preregistration_must_cover_manifest_once_with_cohort(self) -> None:
        corpus = cast(dict[str, object], {
            "tasks": [{
                "task_id": "one",
                "cohort": "repair",
                "stratum": "single-module",
                "workspace_path": "tasks/one",
                "hidden_tests_path": "hidden-tests/one",
                "allowed_edit_paths": ["policy.py"],
                "public_command": ["python3", "-m", "unittest"],
                "hidden_command": ["python3", "-m", "unittest"],
            }]
        })
        preregistration = {
            "analysis": {"random_seed": 1},
            "task_plan": {"tasks": [{
                "task_id": "one",
                "cohort": "repair",
                "stratum": "single-module",
                "execution_order": list(balanced_condition_order(1, 0)),
            }]},
        }
        self.assertEqual([record.task_id for record in records_for_preregistration(corpus, preregistration)], ["one"])
        with self.assertRaisesRegex(ValueError, "every corpus task"):
            _ = records_for_preregistration(corpus, {"analysis": {"random_seed": 1}, "task_plan": {"tasks": []}})

    def test_main_checkpoints_completed_and_interrupted_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            corpus = root / "corpus"
            corpus.mkdir()
            _ = (corpus / "manifest.json").write_text(json.dumps({"tasks": [{
                "task_id": "one",
                "cohort": "repair",
                "stratum": "single-module",
                "workspace_path": "tasks/one",
                "hidden_tests_path": "hidden-tests/one",
                "allowed_edit_paths": ["policy.py"],
                "public_command": [sys.executable, "-m", "unittest"],
                "hidden_command": [sys.executable, "-m", "unittest"],
            }]}), encoding="utf-8")
            prompts = root / "prompts"
            prompts.mkdir()
            for name in ("no_skill.txt", "old_skill.txt", "new_skill.txt"):
                _ = (prompts / name).write_text(name, encoding="utf-8")
            old_skill = root / "old" / "SKILL.md"
            new_skill = root / "new" / "SKILL.md"
            old_skill.parent.mkdir()
            new_skill.parent.mkdir()
            _ = old_skill.write_text("old\n", encoding="utf-8")
            _ = new_skill.write_text("new\n", encoding="utf-8")
            preregistration = root / "preregistration.json"
            protocol = {
                "old_skill_sha256": hashlib.sha256(old_skill.read_bytes()).hexdigest(),
                "new_skill_sha256": hashlib.sha256(new_skill.read_bytes()).hexdigest(),
                "baseline_prompt_sha256": hashlib.sha256((prompts / "no_skill.txt").read_bytes()).hexdigest(),
                "old_skill_prompt_sha256": hashlib.sha256((prompts / "old_skill.txt").read_bytes()).hexdigest(),
                "new_skill_prompt_sha256": hashlib.sha256((prompts / "new_skill.txt").read_bytes()).hexdigest(),
            }
            _ = preregistration.write_text(json.dumps({
                "schema_version": 2,
                "status": "planned",
                "trials": [],
                "scope": {"model_id": "model", "harness_id": "harness"},
                "protocol": protocol,
                "analysis": {"random_seed": 1},
                "preregistration": {},
                "task_plan": {"tasks": [{
                    "task_id": "one",
                    "cohort": "repair",
                    "stratum": "single-module",
                    "execution_order": list(balanced_condition_order(1, 0)),
                }]},
            }), encoding="utf-8")

            def invoke(block: Sequence[Mapping[str, object]], output: Path) -> int:
                by_condition = {cast(str, value["condition"]): value for value in block}

                def fake_execute_condition(**kwargs: object) -> dict[str, object]:
                    return dict(by_condition[cast(str, kwargs["condition"])])

                with patch("run_effect_experiment_v9.execute_condition", side_effect=fake_execute_condition), \
                    patch("run_effect_experiment_v9.validate_preregistration"), \
                    patch("run_effect_experiment_v9.validate_corpus_trees"), \
                    patch("run_effect_experiment_v9.validate_frozen_worktree"), \
                    patch("run_effect_experiment_v9.validate_codex_version"), \
                    patch("run_effect_experiment_v9.audit_collection", return_value={"passed": True, "failures": []}), \
                    patch.object(sys, "argv", [
                    "runner",
                    "--corpus", str(corpus),
                    "--prompts", str(prompts),
                    "--old-skill", str(old_skill),
                    "--new-skill", str(new_skill),
                    "--preregistration", str(preregistration),
                    "--preregistration-commit", "a" * 40,
                    "--raw-output", str(root / output.stem),
                    "--output", str(output),
                    "--seed", "1",
                    "--model", "model",
                    "--harness", "harness",
                    ]):
                    return main()

            complete = [
                {"task_id": "one", "condition": "no_skill", "trial_complete": True, "hidden_repair_pass": False, "scope_ok": True},
                {"task_id": "one", "condition": "old_skill", "trial_complete": True, "hidden_repair_pass": True, "scope_ok": True},
                {"task_id": "one", "condition": "new_skill", "trial_complete": True, "hidden_repair_pass": True, "scope_ok": True},
            ]
            completed_output = root / "completed.json"
            self.assertEqual(invoke(complete, completed_output), 0)
            completed = cast(dict[str, object], json.loads(completed_output.read_text(encoding="utf-8")))
            self.assertEqual(completed["status"], "completed")
            self.assertEqual(len(cast(list[object], completed["trials"])), 3)

            interrupted = list(complete)
            interrupted[0] = dict(interrupted[0]) | {"trial_complete": False}
            interrupted_output = root / "interrupted.json"
            self.assertEqual(invoke(interrupted, interrupted_output), 2)
            saved = cast(dict[str, object], json.loads(interrupted_output.read_text(encoding="utf-8")))
            self.assertEqual(saved["status"], "interrupted")
            self.assertIn("no retry", cast(str, cast(dict[str, object], saved["collection"])["ineligible_reason"]))


if __name__ == "__main__":
    _ = unittest.main()
