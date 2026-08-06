from __future__ import annotations

# The runner is a local script module without a package stub.
# pyright: reportMissingTypeStubs=false

import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from analyze_skill_effect import skill_first_for  # noqa: E402
from run_effect_experiment import TaskRecord, execute_task_pair, run_agent  # noqa: E402


class EffectRunnerTests(unittest.TestCase):
    def test_task_pair_invokes_conditions_in_registered_order(self) -> None:
        task = TaskRecord({
            "task_id": "order-check",
            "stratum": "single-module",
            "function": "order_check",
            "source_path": "tasks/order-check/buggy.py",
            "public_cases_path": "tasks/order-check/public_cases.json",
            "hidden_cases_path": "hidden/order-check.json",
        })
        expected = ("skill", "baseline") if skill_first_for(7, "order-check", 1) else ("baseline", "skill")
        calls: list[str] = []

        def fake_execute_condition(**kwargs: object) -> dict[str, object]:
            condition = str(kwargs["condition"])
            calls.append(condition)
            return {"condition": condition, "hidden_repair_pass": True, "scope_ok": True}

        with patch("run_effect_experiment.execute_condition", side_effect=fake_execute_condition):
            trials = execute_task_pair(
                task=task,
                corpus_root=Path("/tmp/corpus"),
                prompt_dir=Path("/tmp/prompts"),
                skill_copy=Path("/tmp/skill"),
                raw_root=Path("/tmp/raw"),
                codex_path="codex",
                timeout=1.0,
                seed=7,
            )
        self.assertEqual(tuple(calls), expected)
        self.assertEqual([trial["execution_order"] for trial in trials], [1, 2])

    def test_timeout_kills_the_agent_process_group(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            started = time.monotonic()
            exit_code, stdout, stderr = run_agent(
                [sys.executable, "-c", "import time; time.sleep(30)"],
                cwd=Path(directory),
                timeout=0.1,
            )
            elapsed = time.monotonic() - started
        self.assertIsNone(exit_code)
        self.assertEqual(stdout, "")
        self.assertIn("agent timeout after 0.1s", stderr)
        self.assertLess(elapsed, 3.0)

    def test_agent_environment_disables_user_site_and_bytecode(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _ = (root / "module.py").write_text("value = 1\n", encoding="utf-8")
            exit_code, stdout, stderr = run_agent(
                [
                    sys.executable,
                    "-c",
                    "import module; print(module.value)",
                ],
                cwd=root,
                timeout=3.0,
            )
            self.assertEqual(exit_code, 0, stderr)
            self.assertEqual(stdout.strip(), "1")
            self.assertFalse((root / "__pycache__").exists())


if __name__ == "__main__":
    _ = unittest.main()
