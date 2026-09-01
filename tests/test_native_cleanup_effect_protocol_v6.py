from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from typing import cast
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from analyze_native_cleanup_effect_v6 import analyze, canonical_suite_result  # noqa: E402
from create_native_cleanup_effect_preregistration_v6 import (  # noqa: E402
    canonical_sha256,
    create,
    immutable_envelope,
    require_final_new_skill,
    write_preregistration,
)
from materialize_native_cleanup_effect_v6 import materialize_native_cleanup_effect_v6  # noqa: E402
from native_cleanup_effect_runner_v6 import mark_agent_complete, prepare_condition, score_condition  # noqa: E402
import run_native_cleanup_effect_v6_api as api_runner  # noqa: E402


EXPERIMENT = ROOT / "examples" / "effect-experiment-native-v6"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_synthetic_raw(root: Path, preregistration: dict[str, object]) -> None:
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
            (trial / "agent-prompt.txt").write_text("synthetic prompt\n", encoding="utf-8")
            (trial / "agent-transcript.md").write_text("synthetic transcript\n", encoding="utf-8")
            (trial / "agent-result.json").write_text(json.dumps({"status": "agent_exited", "task_id": task_id, "condition": condition}, sort_keys=True) + "\n", encoding="utf-8")
            (trial / "candidate.diff").write_text("", encoding="utf-8")
            score: dict[str, object] = {
                "task_id": task_id,
                "implementation_integrity_passed": True,
                "public_result": {"passed": True},
                "hidden_injected_after_agent_exit": True,
                "hidden_repair_passed": condition == "new_skill",
            }
            score["pre_score_artifact_sha256"] = {
                name: digest(trial / name)
                for name in ("sequence.json", "prepare.json", "seed.txt", "agent-prompt.txt", "agent-transcript.md", "agent-result.json", "candidate.diff")
            }
            (trial / "score.json").write_text(json.dumps(score, sort_keys=True) + "\n", encoding="utf-8")


def one_task_preregistration() -> dict[str, object]:
    record = create(ROOT)
    task_plan = cast(dict[str, object], record["task_plan"])
    task_plan["tasks"] = cast(list[dict[str, object]], task_plan["tasks"])[:1]
    metadata = cast(dict[str, object], record["preregistration"])
    metadata["protocol_sha256"] = canonical_sha256(cast(dict[str, object], record["protocol"]))
    metadata["envelope_sha256"] = canonical_sha256(immutable_envelope(record))
    return record


def apply_reference_fix(workspace: Path, corpus: Path, task_id: str, allowed_paths: list[str]) -> None:
    reference = corpus / "references" / task_id
    for relative in allowed_paths:
        source = reference / relative
        target = workspace / relative
        if source.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            _ = shutil.copy2(source, target)
        elif target.exists():
            target.unlink()


def write_real_raw(root: Path, preregistration: dict[str, object], *, apply_reference: bool = True) -> Path:
    corpus = root / "corpus"
    manifest = materialize_native_cleanup_effect_v6(corpus)
    task = cast(list[dict[str, object]], manifest["tasks"])[0]
    task_id = cast(str, task["task_id"])
    preregistration_path = root / "preregistration.json"
    preregistration_path.write_text(json.dumps(preregistration, sort_keys=True) + "\n", encoding="utf-8")
    raw = root / "raw"
    order = cast(list[str], cast(list[dict[str, object]], cast(dict[str, object], preregistration["task_plan"])["tasks"])[0]["execution_order"])
    for condition in order:
        workspace = root / "workspaces" / condition
        _ = prepare_condition(corpus, preregistration_path, ROOT, raw, task_id, condition, workspace)
        if apply_reference:
            apply_reference_fix(workspace, corpus, task_id, cast(list[str], task["allowed_edit_paths"]))
        transcript = root / "transcripts" / f"{condition}.md"
        transcript.parent.mkdir(exist_ok=True)
        _ = transcript.write_text("Fixture-only native agent transcript.\n", encoding="utf-8")
        mark_agent_complete(
            raw,
            task_id,
            condition,
            agent_id=f"codex-cli:native-v6-fixture-{condition}",
            model_id="gpt-5.5",
            started_at="2026-08-31T20:00:00Z",
            finished_at="2026-08-31T20:00:01Z",
            transcript=transcript,
            executor_kind="codex-cli-api-key",
            exit_code=0,
            auth_mode="api-key",
            skill_search_disabled=True,
            codex_cli_version="codex-cli 0.149.0-alpha.4.1",
        )
        score = score_condition(corpus, raw, task_id, condition, workspace)
        if apply_reference and score["hidden_repair_passed"] is not True:
            raise AssertionError("reference candidate must pass the hidden scorer")
    return raw


class NativeCleanupEffectProtocolV6Tests(unittest.TestCase):
    def test_cli_main_maps_preregistration_option_to_collect_parameter(self) -> None:
        arguments = [
            "runner",
            "--corpus",
            "corpus",
            "--preregistration",
            "plan.json",
            "--source-root",
            "source",
            "--raw-root",
            "raw",
            "--codex",
            "codex-bin",
        ]
        with patch.object(sys, "argv", arguments), patch.object(api_runner, "collect", return_value=[]) as collect:
            self.assertEqual(api_runner.main(), 0)

        self.assertEqual(
            collect.call_args.kwargs,
            {
                "corpus": Path("corpus"),
                "preregistration_path": Path("plan.json"),
                "source_root": Path("source"),
                "raw_root": Path("raw"),
                "codex": "codex-bin",
            },
        )

    def test_canonical_suite_result_ignores_only_volatile_execution_details(self) -> None:
        first = {"passed": True, "returncode": 0, "timeout": False, "stdout": "", "stderr": "Ran 2 tests in 0.001s\nOK\n"}
        second = {"passed": True, "returncode": 0, "timeout": False, "stdout": "", "stderr": "Ran 2 tests in 0.097s\nOK\n"}
        self.assertEqual(canonical_suite_result(first), canonical_suite_result(second))
        changed = {"passed": False, "returncode": 1, "timeout": False, "stdout": "", "stderr": "Ran 2 tests in 0.097s\nFAILED\n"}
        self.assertNotEqual(canonical_suite_result(first), canonical_suite_result(changed))
        failed_score = {
            "passed": False,
            "returncode": 1,
            "timeout": False,
            "stdout": "",
            "stderr": "File \"/private/var/folders/a/b/T/native-cleanup-score-first/candidate/tests/test_hidden.py\", line 7\nAssertionError: stale marker\n",
        }
        failed_replay_stderr = "File \"/private/var/folders/a/b/T/native-cleanup-v6-replay-second/candidate/tests/test_hidden.py\", line 7\nAssertionError: stale marker\n"
        failed_replay = {
            "passed": False,
            "returncode": 1,
            "timeout": False,
            "stdout": "",
            "stderr": failed_replay_stderr,
        }
        self.assertEqual(canonical_suite_result(failed_score), canonical_suite_result(failed_replay))
        altered_assertion = {**failed_replay, "stderr": failed_replay_stderr.replace("stale marker", "different marker")}
        self.assertNotEqual(canonical_suite_result(failed_score), canonical_suite_result(altered_assertion))

    def test_preregistration_creation_hashes_the_frozen_inputs_without_committing_plan(self) -> None:
        created = create(ROOT)
        tasks = cast(list[dict[str, object]], cast(dict[str, object], created["task_plan"])["tasks"])
        self.assertEqual(len(tasks), 10)
        self.assertTrue(all(str(task["task_id"]).startswith("cleanup_v10_") for task in tasks))
        self.assertIn("predecessor blind-score", cast(str, cast(dict[str, object], created["protocol"])["pairing"]))
        protocol = cast(dict[str, object], created["protocol"])
        self.assertEqual(
            protocol["old_skill_sha256"],
            hashlib.sha256((ROOT / "examples/effect-experiment-native-v5/skills/new/SKILL.md").read_bytes()).hexdigest(),
        )
        self.assertEqual(protocol["executor_kind"], "codex-cli-api-key")
        self.assertTrue(protocol["skill_search_disabled_for_all_conditions"])
        self.assertIn("run_native_cleanup_effect_v6_api.py", cast(str, protocol["executor_path"]))

    def test_preregistration_writer_refuses_placeholder_new_skill_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            placeholder = Path(directory) / "SKILL.md"
            placeholder.write_text("placeholder new Skill snapshot\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "placeholder new Skill snapshot"):
                require_final_new_skill(placeholder)

    def test_analyzer_rejects_synthetic_scores_and_replays_real_scores(self) -> None:
        synthetic = create(ROOT)
        with tempfile.TemporaryDirectory() as directory:
            raw_root = Path(directory) / "raw"
            raw_root.mkdir()
            write_synthetic_raw(raw_root, synthetic)
            fabricated = analyze(synthetic, raw_root, root=ROOT)
            self.assertEqual(fabricated["analysis_eligibility"], "ineligible")
            self.assertIn("lacks the preregistered executor provenance", " ".join(cast(list[str], cast(dict[str, object], fabricated["collection"])["errors"])))

        preregistration = one_task_preregistration()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw_root = write_real_raw(root, preregistration)
            complete = analyze(preregistration, raw_root, root=ROOT)
            self.assertEqual(complete["analysis_eligibility"], "eligible")
            self.assertEqual(cast(str, complete["conclusion"]).split(":", 1)[0], "no_demonstrated_improvement")
            self.assertEqual(cast(dict[str, object], complete["collection"])["planned_trials"], 3)

            task = cast(list[dict[str, object]], cast(dict[str, object], preregistration["task_plan"])["tasks"])[0]
            task_id = cast(str, task["task_id"])
            second = cast(list[str], task["execution_order"])[1]
            sequence_path = raw_root / task_id / second / "sequence.json"
            sequence = json.loads(sequence_path.read_text(encoding="utf-8"))
            sequence["predecessor_score_sha256"][0]["sha256"] = "0" * 64
            sequence_path.write_text(json.dumps(sequence, sort_keys=True) + "\n", encoding="utf-8")
            score_path = raw_root / task_id / second / "score.json"
            score = json.loads(score_path.read_text(encoding="utf-8"))
            score["pre_score_artifact_sha256"]["sequence.json"] = digest(sequence_path)
            score_path.write_text(json.dumps(score, sort_keys=True) + "\n", encoding="utf-8")
            invalid_chain = analyze(preregistration, raw_root, root=ROOT)
            self.assertEqual(invalid_chain["analysis_eligibility"], "ineligible")
            self.assertIn("sequence credential", " ".join(cast(list[str], cast(dict[str, object], invalid_chain["collection"])["errors"])))

    def test_analyzer_accepts_complete_failed_hidden_samples(self) -> None:
        preregistration = one_task_preregistration()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw_root = write_real_raw(root, preregistration, apply_reference=False)
            analyzed = analyze(preregistration, raw_root, root=ROOT)
            self.assertEqual(analyzed["analysis_eligibility"], "eligible")
            self.assertEqual(cast(dict[str, object], analyzed["collection"])["completed_trials"], 3)
            task = cast(list[dict[str, object]], cast(dict[str, object], preregistration["task_plan"])["tasks"])[0]
            first_condition = cast(list[str], task["execution_order"])[0]
            self.assertEqual((raw_root / cast(str, task["task_id"]) / first_condition / "candidate.diff").read_text(encoding="utf-8"), "")
            primary = cast(dict[str, object], cast(dict[str, object], analyzed["statistics"])["primary_new_skill_minus_old_skill"])
            self.assertEqual(primary["effect"], 0.0)

    def test_analyzer_rejects_candidate_diff_tampering_after_scoring(self) -> None:
        preregistration = one_task_preregistration()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw_root = write_real_raw(root, preregistration)
            task = cast(list[dict[str, object]], cast(dict[str, object], preregistration["task_plan"])["tasks"])[0]
            condition = cast(list[str], task["execution_order"])[0]
            candidate_diff = raw_root / cast(str, task["task_id"]) / condition / "candidate.diff"
            candidate_diff.write_text("tampered after blind score\n", encoding="utf-8")
            invalid = analyze(preregistration, raw_root, root=ROOT)
            self.assertEqual(invalid["analysis_eligibility"], "ineligible")
            self.assertIn("pre-score artifact binding", " ".join(cast(list[str], cast(dict[str, object], invalid["collection"])["errors"])))

    def test_analyzer_rejects_an_unexpected_retry_directory(self) -> None:
        preregistration = one_task_preregistration()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw_root = write_real_raw(root, preregistration)
            task = cast(list[dict[str, object]], cast(dict[str, object], preregistration["task_plan"])["tasks"])[0]
            retry = raw_root / cast(str, task["task_id"]) / "old_skill_retry"
            retry.mkdir()
            invalid = analyze(preregistration, raw_root, root=ROOT)
            self.assertEqual(invalid["analysis_eligibility"], "ineligible")
            self.assertIn("unexpected trial directories", " ".join(cast(list[str], cast(dict[str, object], invalid["collection"])["errors"])))

    def test_analyzer_rejects_unplanned_task_directory_and_task_file(self) -> None:
        preregistration = one_task_preregistration()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw_root = write_real_raw(root, preregistration)
            (raw_root / "native_v6_unplanned_task").mkdir()
            invalid_extra_task = analyze(preregistration, raw_root, root=ROOT)
            self.assertEqual(invalid_extra_task["analysis_eligibility"], "ineligible")
            self.assertIn("unexpected task directories", " ".join(cast(list[str], cast(dict[str, object], invalid_extra_task["collection"])["errors"])))

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw_root = write_real_raw(root, preregistration)
            task = cast(list[dict[str, object]], cast(dict[str, object], preregistration["task_plan"])["tasks"])[0]
            (raw_root / cast(str, task["task_id"]) / "orphan.txt").write_text("unexpected\n", encoding="utf-8")
            invalid_task_file = analyze(preregistration, raw_root, root=ROOT)
            self.assertEqual(invalid_task_file["analysis_eligibility"], "ineligible")
            self.assertIn("unexpected task files", " ".join(cast(list[str], cast(dict[str, object], invalid_task_file["collection"])["errors"])))

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
