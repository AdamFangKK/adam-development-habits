from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import cast


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from analyze_native_cleanup_effect_v2 import analyze, load_object  # noqa: E402
from create_native_cleanup_effect_preregistration_v2 import create, write_preregistration  # noqa: E402


EXPERIMENT = ROOT / "examples" / "effect-experiment-native-v2"


def write_complete_raw(root: Path, preregistration: dict[str, object]) -> None:
    tasks = cast(list[dict[str, object]], cast(dict[str, object], preregistration["task_plan"])["tasks"])
    for task in tasks:
        task_id = cast(str, task["task_id"])
        for condition in cast(list[str], task["execution_order"]):
            trial = root / task_id / condition
            trial.mkdir(parents=True)
            (trial / "prepare.json").write_text("{}\n", encoding="utf-8")
            (trial / "seed.txt").write_text("a" * 40 + "\n", encoding="utf-8")
            (trial / "candidate.diff").write_text("", encoding="utf-8")
            (trial / "agent-result.json").write_text('{"status":"completed"}\n', encoding="utf-8")
            score = {
                "task_id": task_id,
                "implementation_integrity_passed": True,
                "public_result": {"passed": True},
                "hidden_injected_after_agent_exit": True,
                "hidden_repair_passed": condition == "new_skill",
            }
            (trial / "score.json").write_text(json.dumps(score, sort_keys=True) + "\n", encoding="utf-8")


class NativeCleanupEffectProtocolV2Tests(unittest.TestCase):
    def test_committed_preregistration_matches_the_frozen_inputs(self) -> None:
        committed = load_object(EXPERIMENT / "preregistration.json")
        self.assertEqual(committed, create(ROOT))
        tasks = cast(list[dict[str, object]], cast(dict[str, object], committed["task_plan"])["tasks"])
        self.assertEqual(len(tasks), 10)
        self.assertTrue(all(str(task["task_id"]).startswith("native_v2_") for task in tasks))
        self.assertEqual({task["cohort"] for task in tasks}, {"decision-retention", "repair"})

    def test_preregistration_writer_refuses_to_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "preregistration.json"
            _ = write_preregistration(output, root=ROOT)
            with self.assertRaises(FileExistsError):
                _ = write_preregistration(output, root=ROOT)

    def test_analyzer_requires_a_complete_nonretried_collection(self) -> None:
        preregistration = load_object(EXPERIMENT / "preregistration.json")
        with tempfile.TemporaryDirectory() as directory:
            raw_root = Path(directory) / "raw"
            raw_root.mkdir()
            write_complete_raw(raw_root, preregistration)
            complete = analyze(preregistration, raw_root, root=ROOT)
            self.assertEqual(complete["analysis_eligibility"], "eligible")
            self.assertEqual(complete["conclusion"].split(":", 1)[0], "demonstrated_improvement")
            self.assertEqual(complete["collection"]["planned_trials"], 30)

            retry = raw_root / "native_v2_cleanup_tenant_casefold" / "new_skill_retry"
            retry.mkdir()
            ineligible = analyze(preregistration, raw_root, root=ROOT)
            self.assertEqual(ineligible["analysis_eligibility"], "ineligible")
            self.assertIn("unexpected trial directories", " ".join(cast(list[str], ineligible["collection"]["errors"])))

    def test_analyzer_rejects_a_missing_or_incomplete_trial(self) -> None:
        preregistration = load_object(EXPERIMENT / "preregistration.json")
        with tempfile.TemporaryDirectory() as directory:
            raw_root = Path(directory) / "raw"
            raw_root.mkdir()
            write_complete_raw(raw_root, preregistration)
            missing = raw_root / "native_v2_cleanup_tenant_casefold" / "old_skill" / "candidate.diff"
            missing.unlink()
            result = analyze(preregistration, raw_root, root=ROOT)
            self.assertEqual(result["analysis_eligibility"], "ineligible")
            self.assertIn("missing required artifacts", " ".join(cast(list[str], result["collection"]["errors"])))


if __name__ == "__main__":
    _ = unittest.main()
