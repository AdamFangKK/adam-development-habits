from __future__ import annotations

import json
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path
from typing import cast


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from audit_effect_isolation_v9 import audit_collection  # noqa: E402


class EffectIsolationV9Tests(unittest.TestCase):
    def make_trial(self, root: Path, task_id: str, condition: str, *, wrong_snapshot: bool = False) -> dict[str, object]:
        artifact = root / task_id / condition
        artifact.mkdir(parents=True)
        old = root / "old" / "SKILL.md"
        new = root / "new" / "SKILL.md"
        old.parent.mkdir(exist_ok=True)
        new.parent.mkdir(exist_ok=True)
        _ = old.write_text("old\n", encoding="utf-8")
        _ = new.write_text("new\n", encoding="utf-8")
        supplied = str((new if condition == "new_skill" else old).resolve())
        if wrong_snapshot:
            supplied = str(old.resolve())
        command = f"cat {supplied}"
        event = {
            "type": "item.completed",
            "item": {
                "type": "command_execution",
                "command": command,
                "exit_code": 0,
                "status": "completed",
                "aggregated_output": (new if condition == "new_skill" else old).read_text(encoding="utf-8"),
            },
        }
        _ = (artifact / "agent.stdout.log").write_text(
            (json.dumps(event) + "\n") if condition != "no_skill" else "",
            encoding="utf-8",
        )
        _ = (artifact / "agent.stderr.log").write_text("V9 isolation wrapper: --disable skill_search\n", encoding="utf-8")
        _ = (artifact / "agent-output.md").write_text("summary\n", encoding="utf-8")
        _ = (artifact / "candidate.diff").write_text("diff\n", encoding="utf-8")
        _ = (artifact / "public.json").write_text("{}\n", encoding="utf-8")
        _ = (artifact / "hidden-score.json").write_text(json.dumps({
            "passed": True,
            "implementation_integrity_passed": True,
        }) + "\n", encoding="utf-8")
        return {
            "task_id": task_id,
            "condition": condition,
            "artifact_path": f"{task_id}/{condition}",
            "hidden_repair_pass": True,
            "hidden_scorer_pass": True,
            "public_pass": False,
            "implementation_integrity_passed": True,
            "skill_snapshot_integrity_passed": True,
            "skill_snapshot_sha256": hashlib.sha256((new if condition == "new_skill" else old).read_bytes()).hexdigest() if condition != "no_skill" else None,
            "agent_output_present": True,
        }

    def test_passes_only_with_all_three_isolated_conditions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            trials = [self.make_trial(root, "t1", condition) for condition in ("no_skill", "old_skill", "new_skill")]
            result = root / "result.json"
            _ = result.write_text(json.dumps({"task_plan": {"tasks": [{"task_id": "t1"}]}, "trials": trials}), encoding="utf-8")
            report = audit_collection(root, result, old_skill=root / "old/SKILL.md", new_skill=root / "new/SKILL.md")
            self.assertTrue(report["passed"], report)

    def test_rejects_wrong_snapshot_and_missing_absolute_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            trials = [self.make_trial(root, "t1", condition, wrong_snapshot=condition == "new_skill") for condition in ("no_skill", "old_skill", "new_skill")]
            (root / "t1" / "new_skill" / "agent-output.md").unlink()
            result = root / "result.json"
            _ = result.write_text(json.dumps({"task_plan": {"tasks": [{"task_id": "t1"}]}, "trials": trials}), encoding="utf-8")
            report = audit_collection(root, result, old_skill=root / "old/SKILL.md", new_skill=root / "new/SKILL.md")
            self.assertFalse(report["passed"])
            failures = cast(list[str], report["failures"])
            self.assertTrue(any("snapshot" in failure or "agent-output" in failure for failure in failures))

    def test_rejects_self_reported_snapshot_path_without_full_read(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            trials = [self.make_trial(root, "t1", condition) for condition in ("no_skill", "old_skill", "new_skill")]
            artifact = root / "t1" / "new_skill"
            _ = (artifact / "agent.stdout.log").write_text(
                json.dumps({
                    "type": "item.completed",
                    "item": {
                        "type": "command_execution",
                        "command": f"cat {root / 'new' / 'SKILL.md'}",
                        "exit_code": 0,
                        "status": "completed",
                        "aggregated_output": "new\n",
                    },
                }) + "\n",
                encoding="utf-8",
            )
            result = root / "result.json"
            _ = result.write_text(json.dumps({"task_plan": {"tasks": [{"task_id": "t1"}]}, "trials": trials}), encoding="utf-8")
            report = audit_collection(root, result, old_skill=root / "old/SKILL.md", new_skill=root / "new/SKILL.md")
            self.assertFalse(report["passed"])
            failures = cast(list[str], report["failures"])
            self.assertTrue(any("did not complete a full read" in failure for failure in failures))

    def test_rejects_truncated_skill_read(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            trials = [self.make_trial(root, "t1", condition) for condition in ("no_skill", "old_skill", "new_skill")]
            artifact = root / "t1" / "new_skill"
            _ = (artifact / "agent.stdout.log").write_text(
                json.dumps({
                    "type": "item.completed",
                    "item": {
                        "type": "command_execution",
                        "command": f"cat {root / 'new' / 'SKILL.md'} | head -1",
                        "exit_code": 0,
                        "status": "completed",
                        "aggregated_output": "new\n",
                    },
                }) + "\n",
                encoding="utf-8",
            )
            result = root / "result.json"
            _ = result.write_text(json.dumps({"task_plan": {"tasks": [{"task_id": "t1"}]}, "trials": trials}), encoding="utf-8")
            report = audit_collection(root, result, old_skill=root / "old/SKILL.md", new_skill=root / "new/SKILL.md")
            self.assertFalse(report["passed"])
            failures = cast(list[str], report["failures"])
            self.assertTrue(any("did not complete a full read" in failure for failure in failures))


if __name__ == "__main__":
    _ = unittest.main()
