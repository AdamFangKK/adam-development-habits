"""Keep V7's invalid collection from being reused as effect evidence."""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path
from typing import cast


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "examples" / "effect-experiment-v7"
RAW = EXPERIMENT / "raw"
GLOBAL_SKILL_PATH = "/Users/adamfang/.codex/skills/adam-development-habits/SKILL.md"
FROZEN_PREREGISTRATION_SHA256 = "c726b5e74642e90f2df8b7a4759413b702de9fbf4725a81b146dcf50fcaad5f1"


def tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(relative + b"\0" + hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


class EffectExperimentV7InterruptionTests(unittest.TestCase):
    def test_interruption_report_preserves_both_ineligibility_causes(self) -> None:
        report_path = EXPERIMENT / "interruption.json"
        result_path = EXPERIMENT / "result.json"
        preregistration_path = EXPERIMENT / "preregistration.json"
        report = cast(dict[str, object], json.loads(report_path.read_text(encoding="utf-8")))
        result = cast(dict[str, object], json.loads(result_path.read_text(encoding="utf-8")))
        collection = cast(dict[str, object], report["collection"])

        self.assertEqual(report["status"], "interrupted")
        self.assertEqual(result["status"], "interrupted")
        self.assertEqual(collection["analysis_eligibility"], "ineligible")
        self.assertEqual(collection["raw_tree_sha256"], tree_digest(RAW))
        self.assertEqual(collection["result_sha256"], hashlib.sha256(result_path.read_bytes()).hexdigest())
        self.assertEqual(
            hashlib.sha256(preregistration_path.read_bytes()).hexdigest(),
            FROZEN_PREREGISTRATION_SHA256,
        )
        self.assertIn("no retry or partial analysis", str(cast(dict[str, object], result["collection"])["ineligible_reason"]))

        trials = cast(list[dict[str, object]], result["trials"])
        condition_directories = sorted(path.parent for path in RAW.glob("*/*/hidden-score.json"))
        self.assertEqual(len(condition_directories), collection["captured_condition_artifacts"])
        self.assertEqual({path.relative_to(RAW).as_posix() for path in condition_directories}, {str(trial["artifact_path"]) for trial in trials})
        self.assertEqual(sum(bool(trial["trial_complete"]) for trial in trials), collection["completed_agent_conditions"])

        interrupted = cast(list[dict[str, object]], report["interrupted_conditions"])
        self.assertEqual(len(interrupted), collection["interrupted_agent_conditions"])
        self.assertEqual(interrupted[0]["task_id"], "canonical_audit_path")
        self.assertEqual(interrupted[0]["condition"], "baseline")
        self.assertEqual(interrupted[0]["error_class"], "agent_timeout")
        self.assertTrue(bool(interrupted[0]["agent_launched"]))
        self.assertFalse(bool(interrupted[0]["candidate_written"]))
        self.assertEqual(interrupted[0]["elapsed_seconds"], 180.331)
        stderr = (RAW / "canonical_audit_path/baseline/agent.stderr.log").read_text(encoding="utf-8")
        self.assertIn("agent timeout after 180.0s", stderr)

        integrity_failures = cast(list[dict[str, object]], report["integrity_failures"])
        self.assertEqual(len(integrity_failures), 1)
        contamination = integrity_failures[0]
        self.assertEqual(contamination["id"], "baseline-global-skill-contamination")
        self.assertEqual(contamination["kind"], "condition_difference_violation")
        contaminated_logs = cast(list[str], contamination["observed_artifact_paths"])
        self.assertEqual(len(contaminated_logs), 6)
        for relative_path in contaminated_logs:
            self.assertIn("/baseline/agent.stderr.log", relative_path)
            self.assertIn(GLOBAL_SKILL_PATH, (ROOT / relative_path).read_text(encoding="utf-8"))

        self.assertIn("not a valid baseline-versus-Skill comparison", str(contamination["consequence"]))
        self.assertIn("No V7 Skill-effect", str(report["decision"]))

    def test_v7_result_cannot_be_analyzed_as_a_partial_effect_statistic(self) -> None:
        report = cast(dict[str, object], json.loads((EXPERIMENT / "interruption.json").read_text(encoding="utf-8")))
        result = cast(dict[str, object], json.loads((EXPERIMENT / "result.json").read_text(encoding="utf-8")))
        trials = cast(list[dict[str, object]], result["trials"])
        interrupted = cast(list[dict[str, object]], report["interrupted_conditions"])

        self.assertEqual(len(trials), 16)
        self.assertEqual(sum(not bool(trial["trial_complete"]) for trial in trials), 1)
        incomplete = [trial for trial in trials if not bool(trial["trial_complete"])]
        self.assertEqual(len(incomplete), 1)
        self.assertEqual(incomplete[0]["task_id"], interrupted[0]["task_id"])
        self.assertEqual(incomplete[0]["condition"], interrupted[0]["condition"])
        self.assertEqual(incomplete[0]["artifact_path"], str(interrupted[0]["artifact_path"]).removeprefix("examples/effect-experiment-v7/raw/"))
        self.assertEqual(result["status"], "interrupted")


if __name__ == "__main__":
    _ = unittest.main()
