"""Keep the v5 interruption record tied to its captured, non-analyzable evidence."""

from __future__ import annotations

import json
import unittest
from collections import Counter
from hashlib import sha256
from pathlib import Path
from typing import TypedDict, cast


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "examples" / "effect-experiment-v5"
REPORT = EXPERIMENT / "interruption.json"
RAW = EXPERIMENT / "raw"


class Collection(TypedDict):
    analysis_eligibility: str
    captured_condition_artifacts: int
    completed_agent_conditions: int
    error_classes: dict[str, int]
    interrupted_agent_conditions: int
    planned_conditions: int
    raw_tree_sha256: str


class InterruptedCondition(TypedDict):
    candidate_written_before_failure: bool
    condition: str
    error_class: str
    task_id: str


class InterruptionReport(TypedDict):
    collection: Collection
    interrupted_conditions: list[InterruptedCondition]
    status: str


def raw_tree_sha256() -> str:
    lines: list[str] = []
    for path in sorted(candidate for candidate in RAW.rglob("*") if candidate.is_file()):
        relative_path = path.relative_to(RAW).as_posix()
        lines.append(f"{sha256(path.read_bytes()).hexdigest()}  ./{relative_path}\n")
    return sha256("".join(lines).encode("utf-8")).hexdigest()


class EffectExperimentV5InterruptionTests(unittest.TestCase):
    def test_interruption_report_matches_raw_artifacts(self) -> None:
        report = cast(InterruptionReport, json.loads(REPORT.read_text(encoding="utf-8")))
        self.assertEqual(report["status"], "interrupted")
        self.assertEqual(report["collection"]["analysis_eligibility"], "ineligible")
        self.assertEqual(report["collection"]["raw_tree_sha256"], raw_tree_sha256())

        condition_dirs = sorted(path.parent for path in RAW.glob("*/*/hidden-score.json"))
        self.assertEqual(len(condition_dirs), report["collection"]["captured_condition_artifacts"])
        self.assertEqual(len(condition_dirs), report["collection"]["planned_conditions"])

        interrupted = report["interrupted_conditions"]
        self.assertEqual(len(interrupted), report["collection"]["interrupted_agent_conditions"])
        interrupted_keys = {(item["task_id"], item["condition"]) for item in interrupted}
        self.assertEqual(len(interrupted_keys), len(interrupted))

        completed = 0
        observed_errors: Counter[str] = Counter()
        for directory in condition_dirs:
            key = (directory.parent.name, directory.name)
            stderr = (directory / "agent.stderr.log").read_text(encoding="utf-8")
            candidate_written = bool((directory / "candidate.diff").read_text(encoding="utf-8"))
            if key in interrupted_keys:
                entry = next(item for item in interrupted if (item["task_id"], item["condition"]) == key)
                self.assertFalse((directory / "agent-output.md").exists())
                self.assertIn("ERROR:", stderr)
                self.assertEqual(candidate_written, entry["candidate_written_before_failure"])
                if entry["error_class"] == "model_service_503":
                    self.assertIn("503 Service Unavailable", stderr)
                elif entry["error_class"] == "model_service_429":
                    self.assertIn("429 Too Many Requests", stderr)
                else:
                    self.fail(f"unexpected interruption class: {entry['error_class']}")
                observed_errors[entry["error_class"]] += 1
            else:
                self.assertTrue((directory / "agent-output.md").exists())
                completed += 1

        self.assertEqual(completed, report["collection"]["completed_agent_conditions"])
        self.assertEqual(observed_errors, Counter(report["collection"]["error_classes"]))


if __name__ == "__main__":
    _ = unittest.main()
