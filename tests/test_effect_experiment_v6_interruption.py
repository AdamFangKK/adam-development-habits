from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path
from typing import cast


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "examples" / "effect-experiment-v6"
RAW = EXPERIMENT / "raw"


def tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(relative + b"\0" + hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


class EffectExperimentV6InterruptionTests(unittest.TestCase):
    def test_interruption_report_matches_retained_raw_artifacts(self) -> None:
        report = cast(dict[str, object], json.loads((EXPERIMENT / "interruption.json").read_text(encoding="utf-8")))
        result_path = EXPERIMENT / "result.json"
        result = cast(dict[str, object], json.loads(result_path.read_text(encoding="utf-8")))
        collection = cast(dict[str, object], report["collection"])
        result_collection = cast(dict[str, object], result["collection"])

        self.assertEqual(report["status"], "interrupted")
        self.assertEqual(result["status"], "interrupted")
        self.assertEqual(collection["analysis_eligibility"], "ineligible")
        self.assertEqual(collection["raw_tree_sha256"], tree_digest(RAW))
        self.assertEqual(collection["result_sha256"], hashlib.sha256(result_path.read_bytes()).hexdigest())
        self.assertEqual(collection["planned_conditions"], 40)
        self.assertEqual(collection["completed_agent_conditions"], 0)
        self.assertEqual(collection["interrupted_agent_conditions"], 2)
        self.assertIn("no retry or partial analysis", str(result_collection["ineligible_reason"]))

        interrupted = cast(list[dict[str, object]], report["interrupted_conditions"])
        self.assertEqual(len(interrupted), 2)
        for condition in interrupted:
            self.assertEqual(condition["error_class"], "runner_seed_workspace_destination_exists")
            self.assertFalse(condition["agent_launched"])
            self.assertFalse(condition["candidate_written"])
            artifact = EXPERIMENT / "raw" / str(condition["artifact_path"]).split("raw/", 1)[-1]
            self.assertTrue(artifact.is_dir(), artifact)
            stderr = (artifact / "agent.stderr.log").read_text(encoding="utf-8")
            self.assertIn("FileExistsError", stderr)

    def test_v6_result_cannot_be_interpreted_as_a_partial_effect_statistic(self) -> None:
        result = cast(dict[str, object], json.loads((EXPERIMENT / "result.json").read_text(encoding="utf-8")))
        self.assertEqual(result["status"], "interrupted")
        trials = cast(list[dict[str, object]], result["trials"])
        self.assertEqual(len(trials), 2)
        self.assertTrue(all(not bool(trial["trial_complete"]) for trial in trials))
        self.assertIn(
            "no retry or partial analysis",
            str(cast(dict[str, object], result["collection"])["ineligible_reason"]),
        )


if __name__ == "__main__":
    _ = unittest.main()
