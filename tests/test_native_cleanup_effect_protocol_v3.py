from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import cast


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from analyze_native_cleanup_effect_v3 import analyze, load_object  # noqa: E402
from create_native_cleanup_effect_preregistration_v3 import (  # noqa: E402
    canonical_sha256,
    create,
    immutable_envelope,
    write_preregistration,
)


EXPERIMENT = ROOT / "examples" / "effect-experiment-native-v3"
ARTIFACTS = ("sequence.json", "prepare.json", "seed.txt", "agent-result.json", "candidate.diff", "score.json")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_complete_raw(root: Path, preregistration: dict[str, object]) -> None:
    tasks = cast(list[dict[str, object]], cast(dict[str, object], preregistration["task_plan"])["tasks"])
    for task in tasks:
        task_id = cast(str, task["task_id"])
        order = cast(list[str], task["execution_order"])
        for index, condition in enumerate(order):
            trial = root / task_id / condition
            trial.mkdir(parents=True)
            predecessors = [
                {"condition": previous, "sha256": digest(root / task_id / previous / "score.json")}
                for previous in order[:index]
            ]
            sequence = {
                "schema_version": 1,
                "task_id": task_id,
                "condition": condition,
                "condition_index": index + 1,
                "execution_order": order,
                "predecessor_score_sha256": predecessors,
            }
            (trial / "sequence.json").write_text(json.dumps(sequence, sort_keys=True) + "\n", encoding="utf-8")
            seed = "a" * 40
            prepare = {
                "task_id": task_id,
                "condition": condition,
                "allowed_edit_paths": [],
                "seed_commit": seed,
                "predecessor_score_sha256": predecessors,
            }
            (trial / "prepare.json").write_text(json.dumps(prepare, sort_keys=True) + "\n", encoding="utf-8")
            (trial / "seed.txt").write_text(seed + "\n", encoding="utf-8")
            (trial / "agent-result.json").write_text(
                json.dumps({"status": "agent_exited", "task_id": task_id, "condition": condition}, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            (trial / "candidate.diff").write_text("", encoding="utf-8")
            score = {
                "task_id": task_id,
                "implementation_integrity_passed": True,
                "public_result": {"passed": True},
                "hidden_injected_after_agent_exit": True,
                "hidden_repair_passed": condition == "new_skill",
            }
            score["pre_score_artifact_sha256"] = {
                name: digest(trial / name)
                for name in ("sequence.json", "prepare.json", "seed.txt", "agent-result.json", "candidate.diff")
            }
            (trial / "score.json").write_text(json.dumps(score, sort_keys=True) + "\n", encoding="utf-8")


class NativeCleanupEffectProtocolV3Tests(unittest.TestCase):
    def test_committed_preregistration_matches_the_frozen_inputs(self) -> None:
        committed = load_object(EXPERIMENT / "preregistration.json")
        self.assertEqual(committed, create(ROOT))
        tasks = cast(list[dict[str, object]], cast(dict[str, object], committed["task_plan"])["tasks"])
        self.assertEqual(len(tasks), 10)
        self.assertTrue(all(str(task["task_id"]).startswith("native_v3_") for task in tasks))
        self.assertIn("predecessor blind-score", cast(str, cast(dict[str, object], committed["protocol"])["pairing"]))

    def test_preregistration_writer_refuses_to_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "preregistration.json"
            _ = write_preregistration(output, root=ROOT)
            with self.assertRaises(FileExistsError):
                _ = write_preregistration(output, root=ROOT)

    def test_analyzer_accepts_a_complete_chain_and_rejects_retry_or_chain_tampering(self) -> None:
        preregistration = load_object(EXPERIMENT / "preregistration.json")
        with tempfile.TemporaryDirectory() as directory:
            raw_root = Path(directory) / "raw"
            raw_root.mkdir()
            write_complete_raw(raw_root, preregistration)
            complete = analyze(preregistration, raw_root, root=ROOT)
            self.assertEqual(complete["analysis_eligibility"], "eligible")
            self.assertEqual(complete["conclusion"].split(":", 1)[0], "demonstrated_improvement")
            self.assertEqual(complete["collection"]["planned_trials"], 30)

            task = cast(list[dict[str, object]], cast(dict[str, object], preregistration["task_plan"])["tasks"])[0]
            task_id = cast(str, task["task_id"])
            second = cast(list[str], task["execution_order"])[1]
            sequence_path = raw_root / task_id / second / "sequence.json"
            sequence = json.loads(sequence_path.read_text(encoding="utf-8"))
            sequence["predecessor_score_sha256"][0]["sha256"] = "0" * 64
            sequence_path.write_text(json.dumps(sequence, sort_keys=True) + "\n", encoding="utf-8")
            invalid_chain = analyze(preregistration, raw_root, root=ROOT)
            self.assertEqual(invalid_chain["analysis_eligibility"], "ineligible")
            self.assertIn("sequence credential", " ".join(cast(list[str], invalid_chain["collection"]["errors"])))

    def test_analyzer_rejects_candidate_diff_tampering_after_scoring(self) -> None:
        preregistration = load_object(EXPERIMENT / "preregistration.json")
        with tempfile.TemporaryDirectory() as directory:
            raw_root = Path(directory) / "raw"
            raw_root.mkdir()
            write_complete_raw(raw_root, preregistration)
            task = cast(list[dict[str, object]], cast(dict[str, object], preregistration["task_plan"])["tasks"])[0]
            condition = cast(list[str], task["execution_order"])[0]
            candidate_diff = raw_root / cast(str, task["task_id"]) / condition / "candidate.diff"
            candidate_diff.write_text("tampered after blind score\n", encoding="utf-8")
            invalid = analyze(preregistration, raw_root, root=ROOT)
            self.assertEqual(invalid["analysis_eligibility"], "ineligible")
            self.assertIn("pre-score artifact binding", " ".join(cast(list[str], invalid["collection"]["errors"])))

    def test_analyzer_rejects_an_unexpected_retry_directory(self) -> None:
        preregistration = load_object(EXPERIMENT / "preregistration.json")
        with tempfile.TemporaryDirectory() as directory:
            raw_root = Path(directory) / "raw"
            raw_root.mkdir()
            write_complete_raw(raw_root, preregistration)
            task = cast(list[dict[str, object]], cast(dict[str, object], preregistration["task_plan"])["tasks"])[0]
            retry = raw_root / cast(str, task["task_id"]) / "old_skill_retry"
            retry.mkdir()
            invalid = analyze(preregistration, raw_root, root=ROOT)
            self.assertEqual(invalid["analysis_eligibility"], "ineligible")
            self.assertIn("unexpected trial directories", " ".join(cast(list[str], invalid["collection"]["errors"])))

    def test_analyzer_rejects_unplanned_task_directory_and_task_file(self) -> None:
        preregistration = load_object(EXPERIMENT / "preregistration.json")
        with tempfile.TemporaryDirectory() as directory:
            raw_root = Path(directory) / "raw"
            raw_root.mkdir()
            write_complete_raw(raw_root, preregistration)
            (raw_root / "native_v3_unplanned_task").mkdir()
            invalid_extra_task = analyze(preregistration, raw_root, root=ROOT)
            self.assertEqual(invalid_extra_task["analysis_eligibility"], "ineligible")
            self.assertIn("unexpected task directories", " ".join(cast(list[str], invalid_extra_task["collection"]["errors"])))

        with tempfile.TemporaryDirectory() as directory:
            raw_root = Path(directory) / "raw"
            raw_root.mkdir()
            write_complete_raw(raw_root, preregistration)
            task = cast(list[dict[str, object]], cast(dict[str, object], preregistration["task_plan"])["tasks"])[0]
            (raw_root / cast(str, task["task_id"]) / "orphan.txt").write_text("unexpected\n", encoding="utf-8")
            invalid_task_file = analyze(preregistration, raw_root, root=ROOT)
            self.assertEqual(invalid_task_file["analysis_eligibility"], "ineligible")
            self.assertIn("unexpected task files", " ".join(cast(list[str], invalid_task_file["collection"]["errors"])))

    def test_analyzer_rejects_replaced_base_hidden_scorer(self) -> None:
        preregistration = create(ROOT)
        protocol = cast(dict[str, object], preregistration["protocol"])
        protocol["base_runner_sha256"] = "0" * 64
        metadata = cast(dict[str, object], preregistration["preregistration"])
        metadata["protocol_sha256"] = canonical_sha256(protocol)
        metadata["envelope_sha256"] = canonical_sha256(immutable_envelope(preregistration))
        with tempfile.TemporaryDirectory() as directory:
            raw_root = Path(directory) / "raw"
            raw_root.mkdir()
            with self.assertRaisesRegex(ValueError, "base_runner_sha256"):
                _ = analyze(preregistration, raw_root, root=ROOT)


if __name__ == "__main__":
    _ = unittest.main()
