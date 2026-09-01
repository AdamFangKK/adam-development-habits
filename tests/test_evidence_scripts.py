from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
EXAMPLE = ROOT / "assets" / "evidence-ledger.example.json"
CAUSAL_EXAMPLE = ROOT / "examples" / "causal-execution-experiment.json"
CAUSAL_NOTIFICATION_EXAMPLE = ROOT / "examples" / "causal-notification-experiment.json"
HOLISTIC_EVIDENCE = ROOT / ".adam" / "evidence" / "holistic-quality-discipline.json"
CONCISE_EXECUTION_EVIDENCE = ROOT / ".adam" / "evidence" / "adam-skill-concise-execution-optimization.json"
sys.path.insert(0, str(SCRIPTS))

from validate_evidence import validate_evidence  # noqa: E402


class EvidenceScriptTests(unittest.TestCase):
    def test_example_is_valid(self) -> None:
        payload = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        self.assertEqual(validate_evidence(payload), [])

    def test_causal_example_is_valid(self) -> None:
        payload = json.loads(CAUSAL_EXAMPLE.read_text(encoding="utf-8"))
        self.assertEqual(validate_evidence(payload, artifact_root=ROOT), [])

    def test_complex_causal_example_is_valid(self) -> None:
        payload = json.loads(CAUSAL_NOTIFICATION_EXAMPLE.read_text(encoding="utf-8"))
        self.assertEqual(validate_evidence(payload, artifact_root=ROOT), [])

    def test_root_cause_fix_requires_stronger_than_observational_evidence(self) -> None:
        payload = json.loads(CAUSAL_EXAMPLE.read_text(encoding="utf-8"))
        payload["causal"]["evidence_types"] = ["observational"]
        self.assertIn(
            "causal.root_cause_fix requires reproduction or intervention evidence",
            validate_evidence(payload),
        )

    def test_root_cause_fix_requires_a_supported_hypothesis_with_evidence(self) -> None:
        payload = json.loads(CAUSAL_EXAMPLE.read_text(encoding="utf-8"))
        payload["causal"]["hypotheses"][1]["evidence_refs"] = []
        self.assertIn(
            "causal.root_cause_fix requires a supported hypothesis with execution evidence",
            validate_evidence(payload),
        )

    def test_root_cause_fix_rejects_a_supported_hypothesis_backed_only_by_source(self) -> None:
        payload = json.loads(CAUSAL_EXAMPLE.read_text(encoding="utf-8"))
        payload["causal"]["hypotheses"][1]["evidence_refs"] = ["payment-test-source"]
        self.assertIn(
            "causal.root_cause_fix requires a supported hypothesis with execution evidence",
            validate_evidence(payload, artifact_root=ROOT),
        )

    def test_full_causal_evidence_requires_path_and_timeline(self) -> None:
        payload = json.loads(CAUSAL_EXAMPLE.read_text(encoding="utf-8"))
        del payload["causal"]["upstream_path"]
        del payload["causal"]["timeline_evidence"]
        errors = validate_evidence(payload)
        self.assertIn("causal.upstream_path must be a non-empty string for full mode", errors)
        self.assertIn("causal.timeline_evidence must be a non-empty string for full mode", errors)

    def test_root_cause_fix_requires_owner_counterfactual_and_alternative(self) -> None:
        payload = json.loads(CAUSAL_EXAMPLE.read_text(encoding="utf-8"))
        del payload["causal"]["causal_owner"]
        del payload["causal"]["counterfactual"]
        payload["causal"]["hypotheses"] = [payload["causal"]["hypotheses"][1]]
        errors = validate_evidence(payload)
        self.assertIn("causal_owner must be a non-empty string", errors)
        self.assertIn("causal.counterfactual must be an object for root_cause_fix", errors)
        self.assertIn("causal.root_cause_fix requires a rejected or unresolved alternative hypothesis", errors)

    def test_causal_evidence_artifact_hash_is_verified(self) -> None:
        payload = json.loads(CAUSAL_EXAMPLE.read_text(encoding="utf-8"))
        payload["causal"]["evidence_artifacts"][0]["sha256"] = "0" * 64
        self.assertIn(
            "causal.evidence_artifacts[0].sha256 does not match the referenced file",
            validate_evidence(payload, artifact_root=ROOT),
        )

    def test_causal_evidence_artifact_path_cannot_escape_the_repository(self) -> None:
        payload = json.loads(CAUSAL_EXAMPLE.read_text(encoding="utf-8"))
        payload["causal"]["evidence_artifacts"][0]["path"] = "../outside.txt"
        self.assertIn(
            "causal.evidence_artifacts[0].path must stay inside the artifact root",
            validate_evidence(payload, artifact_root=ROOT),
        )

    def test_causal_hypothesis_references_must_name_declared_artifacts(self) -> None:
        payload = json.loads(CAUSAL_EXAMPLE.read_text(encoding="utf-8"))
        payload["causal"]["hypotheses"][1]["evidence_refs"] = ["missing"]
        self.assertIn(
            "causal.hypotheses[1].evidence_refs must name declared evidence artifacts",
            validate_evidence(payload, artifact_root=ROOT),
        )

    def test_causal_experiment_reports_are_reproducible(self) -> None:
        experiments = (
            ("causal-execution-experiment.py", "causal-execution-experiment.report.json"),
            ("causal-notification-experiment.py", "causal-notification-experiment.report.json"),
        )
        for script_name, report_name in experiments:
            with self.subTest(script=script_name):
                result = subprocess.run(
                    [sys.executable, str(ROOT / "examples" / script_name), "--report"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                expected_report = (ROOT / "examples" / report_name).read_text(encoding="utf-8")
                self.assertEqual(result.stdout, expected_report)

    def test_level_two_requires_independent_review(self) -> None:
        payload = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        del payload["independent_review"]
        self.assertIn("independent_review must be an object for level 2", validate_evidence(payload))

    def test_level_two_requires_approved_review(self) -> None:
        payload = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        payload["independent_review"]["outcome"] = "changes_requested"
        self.assertIn("independent_review.outcome must be approved", validate_evidence(payload))

    def test_level_two_rejects_obvious_self_review_labels(self) -> None:
        for reviewer in ("self", "same-agent", "implementer", "automated_contract_tests"):
            with self.subTest(reviewer=reviewer):
                payload = json.loads(EXAMPLE.read_text(encoding="utf-8"))
                payload["independent_review"]["reviewer"] = reviewer
                self.assertIn(
                    "independent_review.reviewer must identify a reviewer independent from the implementer",
                    validate_evidence(payload),
                )

    def test_evidence_requires_a_real_verification(self) -> None:
        payload = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        for verification in payload["verification"]:
            verification["status"] = "not_applicable"
        self.assertIn("verification must contain at least one passed result", validate_evidence(payload))

    def test_schema_version_two_requires_quality_decisions(self) -> None:
        payload = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        del payload["quality_decisions"]
        self.assertIn(
            "quality_decisions is required for schema_version 2",
            validate_evidence(payload),
        )

    def test_schema_version_two_requires_hash_linked_verification_output(self) -> None:
        payload = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        del payload["verification"][0]["evidence_refs"]
        self.assertIn(
            "verification[0].evidence_refs must be a non-empty list for passed schema_version 2 checks",
            validate_evidence(payload),
        )

    def test_schema_version_two_rejects_review_only_verification_evidence(self) -> None:
        payload = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        payload["verification"][0]["evidence_refs"] = ["order-review"]
        self.assertIn(
            "verification[0].evidence_refs must include command_output or test_output evidence",
            validate_evidence(payload),
        )

    def test_schema_version_two_requires_execution_artifact_metadata(self) -> None:
        requirements = {
            "command": "command must be a non-empty string",
            "exit_code": "exit_code must be an integer",
            "executed_at": "executed_at must be an RFC 3339 UTC timestamp",
            "repository_revision": "repository_revision must be a full lowercase Git commit SHA",
        }
        for field, message in requirements.items():
            with self.subTest(field=field):
                payload = json.loads(EXAMPLE.read_text(encoding="utf-8"))
                del payload["supporting_artifacts"][0][field]
                self.assertTrue(
                    any(message in error for error in validate_evidence(payload)),
                    validate_evidence(payload),
                )

    def test_schema_version_two_rejects_placeholder_or_unknown_repository_revision(self) -> None:
        directory = self._make_repository(include_evidence=True)
        artifact = directory / ".adam" / "evidence" / "order-api-migration.json"
        for revision, message in (
            ("0" * 40 + "+worktree", "must be a full lowercase Git commit SHA"),
            ("f" * 40 + "+worktree", "must reference a commit in the artifact repository"),
        ):
            with self.subTest(revision=revision):
                payload = json.loads(artifact.read_text(encoding="utf-8"))
                payload["supporting_artifacts"][0]["repository_revision"] = revision
                self.assertTrue(
                    any(message in error for error in validate_evidence(payload, artifact_root=directory)),
                    validate_evidence(payload, artifact_root=directory),
                )

    def test_schema_version_two_binds_passed_verification_to_successful_same_command_output(self) -> None:
        for field, value in (("command", "pnpm test -- unrelated"), ("exit_code", 1)):
            with self.subTest(field=field):
                payload = json.loads(EXAMPLE.read_text(encoding="utf-8"))
                payload["supporting_artifacts"][0][field] = value
                self.assertIn(
                    "verification[0].evidence_refs must include successful output bound to the same command",
                    validate_evidence(payload),
                )

    def test_schema_version_two_requires_hash_linked_independent_review(self) -> None:
        payload = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        del payload["independent_review"]["evidence_ref"]
        self.assertIn(
            "independent_review.evidence_ref must be a non-empty string for schema_version 2",
            validate_evidence(payload),
        )

    def test_schema_version_one_keeps_legacy_quality_decision_compatibility(self) -> None:
        payload = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        payload["schema_version"] = 1
        del payload["quality_decisions"]
        self.assertEqual(validate_evidence(payload), [])

    def test_quality_decisions_require_every_normative_field(self) -> None:
        payload = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        del payload["quality_decisions"]["threat_boundary"]
        self.assertIn(
            "quality_decisions.threat_boundary must be an object",
            validate_evidence(payload),
        )

    def test_quality_decisions_require_delivery_lifecycle(self) -> None:
        payload = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        del payload["quality_decisions"]["delivery_lifecycle"]
        self.assertIn(
            "quality_decisions.delivery_lifecycle must be an object",
            validate_evidence(payload),
        )

    def test_quality_decisions_reject_unknown_status(self) -> None:
        payload = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        payload["quality_decisions"]["error_model"]["status"] = "pending"
        self.assertIn(
            "quality_decisions.error_model.status must be applied or not_applicable",
            validate_evidence(payload),
        )

    def test_supporting_artifact_hash_is_verified(self) -> None:
        payload = json.loads(HOLISTIC_EVIDENCE.read_text(encoding="utf-8"))
        payload["supporting_artifacts"][0]["sha256"] = "0" * 64
        self.assertIn(
            "supporting_artifacts[0].sha256 does not match the referenced file",
            validate_evidence(payload, artifact_root=ROOT),
        )

    def test_supporting_artifact_path_cannot_escape_the_repository(self) -> None:
        payload = json.loads(HOLISTIC_EVIDENCE.read_text(encoding="utf-8"))
        payload["supporting_artifacts"][0]["path"] = "../outside.txt"
        self.assertIn(
            "supporting_artifacts[0].path must stay inside the artifact root",
            validate_evidence(payload, artifact_root=ROOT),
        )

    def test_supporting_artifact_absolute_path_is_rejected(self) -> None:
        payload = json.loads(HOLISTIC_EVIDENCE.read_text(encoding="utf-8"))
        payload["supporting_artifacts"][0]["path"] = "/tmp/outside.txt"
        self.assertIn(
            "supporting_artifacts[0].path must stay inside the artifact root",
            validate_evidence(payload, artifact_root=ROOT),
        )

    def test_supporting_artifact_must_reference_a_file(self) -> None:
        payload = json.loads(HOLISTIC_EVIDENCE.read_text(encoding="utf-8"))
        payload["supporting_artifacts"][0]["path"] = "examples/missing-evidence.json"
        self.assertIn(
            "supporting_artifacts[0].path does not reference a file",
            validate_evidence(payload, artifact_root=ROOT),
        )

    def test_supporting_artifact_ids_must_be_unique(self) -> None:
        payload = json.loads(HOLISTIC_EVIDENCE.read_text(encoding="utf-8"))
        payload["supporting_artifacts"][1]["id"] = payload["supporting_artifacts"][0]["id"]
        self.assertIn(
            "supporting_artifacts[1].id must be unique",
            validate_evidence(payload, artifact_root=ROOT),
        )

    def test_supporting_artifact_kind_must_be_supported(self) -> None:
        payload = json.loads(HOLISTIC_EVIDENCE.read_text(encoding="utf-8"))
        payload["supporting_artifacts"][0]["kind"] = "unknown_kind"
        self.assertIn(
            "supporting_artifacts[0].kind must be command_output, diff, evaluation_transcript, review_report, or test_output",
            validate_evidence(payload, artifact_root=ROOT),
        )

    def test_historical_supporting_artifact_is_verified_from_its_git_commit(self) -> None:
        directory = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, directory, True)
        self._git(directory, "init")
        self._git(directory, "config", "user.name", "Evidence Test")
        self._git(directory, "config", "user.email", "evidence-test@example.invalid")
        artifact_path = directory / "report.txt"
        original = b"original evidence\n"
        artifact_path.write_bytes(original)
        self._git(directory, "add", "report.txt")
        self._git(directory, "commit", "-m", "record evidence")
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=directory, text=True).strip()
        artifact_path.write_text("new report\n", encoding="utf-8")

        payload = json.loads(HOLISTIC_EVIDENCE.read_text(encoding="utf-8"))
        payload["supporting_artifacts"] = [
            {
                "id": "historical-report",
                "kind": "test_output",
                "path": "report.txt",
                "git_commit": commit,
                "sha256": hashlib.sha256(original).hexdigest(),
                "summary": "Evidence frozen at the declared commit.",
            }
        ]
        self.assertEqual(validate_evidence(payload, artifact_root=directory), [])

    def test_historical_supporting_artifact_rejects_an_unknown_commit(self) -> None:
        payload = json.loads(HOLISTIC_EVIDENCE.read_text(encoding="utf-8"))
        payload["supporting_artifacts"][0]["git_commit"] = "0" * 40
        self.assertIn(
            "supporting_artifacts[0].git_commit does not reference a commit in the artifact repository",
            validate_evidence(payload, artifact_root=ROOT),
        )

    def test_concise_execution_evidence_pins_historical_contract_tests(self) -> None:
        payload = json.loads(CONCISE_EXECUTION_EVIDENCE.read_text(encoding="utf-8"))
        expected_commit = "97d27dc5efbfea45ea4a8a95f4dae699818a8d01"
        expected_sha256 = "5ae2dba58f8b22ef91f52a2af4b57f0f4ef9fdda10a165dcdd5f56432b683fa9"
        artifacts = (
            payload["supporting_artifacts"][12],
            payload["causal"]["evidence_artifacts"][1],
        )

        for artifact in artifacts:
            with self.subTest(artifact=artifact["id"]):
                self.assertEqual(artifact["path"], "tests/test_skill_contract.py")
                self.assertEqual(artifact["git_commit"], expected_commit)
                self.assertEqual(artifact["sha256"], expected_sha256)

        self.assertEqual(validate_evidence(payload, artifact_root=ROOT), [])

    def test_code_change_requires_evidence_when_enabled(self) -> None:
        without_evidence = self._make_repository(include_evidence=False)
        with self.subTest("missing evidence fails"):
            result = self._run_gate(without_evidence)
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertIn("behavioral changes require", result.stderr)

        with_evidence = self._make_repository(include_evidence=True)
        with self.subTest("valid evidence passes"):
            result = self._run_gate(with_evidence)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("valid changed evidence", result.stdout)

    def test_new_schema_version_one_evidence_cannot_satisfy_the_behavior_gate(self) -> None:
        directory = self._make_repository(include_evidence=True, evidence_schema_version=1)
        result = self._run_gate(directory)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("valid changed schema_version 2 evidence artifact", result.stderr)

    def test_deleted_code_requires_evidence_when_enabled(self) -> None:
        directory = self._make_repository(include_evidence=False, delete_source=True)
        result = self._run_gate(directory)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("behavioral changes require", result.stderr)

    def test_common_module_source_requires_evidence_when_enabled(self) -> None:
        directory = self._make_repository(include_evidence=False, source_name="module.mjs")
        result = self._run_gate(directory)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("behavioral changes require", result.stderr)

    def test_runtime_configuration_requires_evidence_when_enabled(self) -> None:
        directory = self._make_repository(include_evidence=False, source_name="service.yaml")
        result = self._run_gate(directory)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("behavioral changes require", result.stderr)

    def test_infrastructure_configuration_requires_evidence_when_enabled(self) -> None:
        directory = self._make_repository(include_evidence=False, source_name="infrastructure/main.tf")
        result = self._run_gate(directory)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("behavioral changes require", result.stderr)

    def test_secret_environment_files_require_level_two_evidence(self) -> None:
        for source_name in (".env", ".env.production", "config/.env", "secret.env"):
            with self.subTest(source_name=source_name):
                directory = self._make_repository(
                    include_evidence=False,
                    source_name=source_name,
                    source_initial="EXAMPLE=false\n",
                    source_changed="EXAMPLE=true\n",
                )
                result = self._run_gate(directory, require_level_two_for_high_risk=True)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIn("behavioral changes require", result.stderr)

    def test_extensionless_shebang_script_requires_evidence_when_enabled(self) -> None:
        directory = self._make_repository(
            include_evidence=False,
            source_name="deploy",
            source_initial="#!/usr/bin/env sh\necho before\n",
            source_changed="#!/usr/bin/env sh\necho after\n",
        )
        result = self._run_gate(directory)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("behavioral changes require", result.stderr)

    def test_high_risk_change_requires_level_two_when_enabled(self) -> None:
        directory = self._make_repository(
            include_evidence=True,
            source_name="src/payments/charge.py",
            evidence_level=1,
        )
        result = self._run_gate(directory, require_level_two_for_high_risk=True)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("high-risk behavioral changes require", result.stderr)

    def test_high_risk_change_passes_with_level_two_when_enabled(self) -> None:
        directory = self._make_repository(
            include_evidence=True,
            source_name="src/payments/charge.py",
            evidence_level=2,
        )
        result = self._run_gate(directory, require_level_two_for_high_risk=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_schema_version_one_level_two_cannot_satisfy_the_high_risk_gate(self) -> None:
        directory = self._make_repository(
            include_evidence=True,
            source_name="src/payments/charge.py",
            evidence_level=2,
            evidence_schema_version=1,
        )
        result = self._run_gate(directory, require_level_two_for_high_risk=True)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("schema_version 2 level 2 evidence artifact", result.stderr)

    def test_frontend_behavior_files_require_evidence(self) -> None:
        for source_name in ("src/page.html", "src/styles.css", "src/theme.scss", "src/view.mdx"):
            with self.subTest(source_name=source_name):
                directory = self._make_repository(include_evidence=False, source_name=source_name)
                result = self._run_gate(directory)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIn("behavioral changes require", result.stderr)

    def test_deleted_extensionless_shebang_script_requires_evidence_when_enabled(self) -> None:
        directory = self._make_repository(
            include_evidence=False,
            delete_source=True,
            source_name="runner",
            source_initial="#!/usr/bin/env sh\necho before\n",
        )
        result = self._run_gate(directory)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("behavioral changes require", result.stderr)

    def test_documentation_configuration_does_not_require_evidence(self) -> None:
        directory = self._make_repository(include_evidence=False, source_name="docs/example.yaml")
        result = self._run_gate(directory)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("no behavior-changing files changed", result.stdout)

    def test_include_working_tree_detects_an_untracked_behavioral_file(self) -> None:
        directory = self._make_repository(include_evidence=False)
        untracked = directory / "scripts" / "local-precommit.py"
        untracked.parent.mkdir(exist_ok=True)
        untracked.write_text("VALUE = 3\n", encoding="utf-8")
        result = self._run_gate(directory, base="HEAD", include_working_tree=True)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("behavioral changes require", result.stderr)

    def test_evidence_filename_must_match_change_id(self) -> None:
        directory = self._make_repository(
            include_evidence=True,
            evidence_name="mismatched-change-id.json",
        )
        result = self._run_gate(directory)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("change_id must match the evidence artifact filename", result.stderr)

    def test_validator_checks_evidence_filename(self) -> None:
        directory = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, directory, True)
        artifact = directory / ".adam" / "evidence" / "mismatched-change-id.json"
        artifact.parent.mkdir(parents=True)
        shutil.copy(EXAMPLE, artifact)
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "validate_evidence.py"), str(artifact)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("change_id must match the evidence artifact filename", result.stderr)

    def test_replaced_evidence_does_not_block_a_valid_new_artifact(self) -> None:
        directory = self._make_repository(
            include_evidence=True,
            baseline_evidence=True,
            remove_baseline_evidence=True,
        )
        result = self._run_gate(directory)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("valid changed evidence", result.stdout)

    def test_absolute_evidence_directory_is_normalized(self) -> None:
        directory = self._make_repository(include_evidence=True)
        result = self._run_gate(directory, evidence_dir=directory / ".adam" / "evidence")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("valid changed evidence", result.stdout)

    def test_gate_rejects_a_stale_causal_evidence_artifact(self) -> None:
        directory = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, directory, True)
        self._git(directory, "init")
        self._git(directory, "config", "user.name", "Evidence Test")
        self._git(directory, "config", "user.email", "evidence-test@example.invalid")
        (directory / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
        self._git(directory, "add", "app.py")
        self._git(directory, "commit", "-m", "baseline")

        example_path = directory / "examples" / "causal-execution-experiment.py"
        example_path.parent.mkdir()
        shutil.copy(ROOT / "examples" / "causal-execution-experiment.py", example_path)
        example_path.write_text(example_path.read_text(encoding="utf-8") + "# stale evidence\n", encoding="utf-8")
        evidence = json.loads(CAUSAL_EXAMPLE.read_text(encoding="utf-8"))
        evidence["change_id"] = "stale-causal-evidence"
        artifact = directory / ".adam" / "evidence" / "stale-causal-evidence.json"
        artifact.parent.mkdir(parents=True)
        artifact.write_text(json.dumps(evidence), encoding="utf-8")
        (directory / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
        self._git(directory, "add", "-A")
        self._git(directory, "commit", "-m", "code change")

        result = self._run_gate(directory)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("sha256 does not match the referenced file", result.stderr)

    def _make_repository(
        self,
        *,
        include_evidence: bool,
        delete_source: bool = False,
        source_name: str = "app.py",
        baseline_evidence: bool = False,
        evidence_name: str = "order-api-migration.json",
        evidence_level: int | None = None,
        evidence_schema_version: int | None = None,
        remove_baseline_evidence: bool = False,
        source_initial: str = "VALUE = 1\n",
        source_changed: str = "VALUE = 2\n",
    ) -> Path:
        directory = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, directory, True)
        self._git(directory, "init")
        self._git(directory, "config", "user.name", "Evidence Test")
        self._git(directory, "config", "user.email", "evidence-test@example.invalid")
        source = directory / source_name
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(source_initial, encoding="utf-8")
        if baseline_evidence:
            evidence_dir = directory / ".adam" / "evidence"
            evidence_dir.mkdir(parents=True)
            shutil.copy(EXAMPLE, evidence_dir / "obsolete.json")
        self._git(directory, "add", source_name)
        if baseline_evidence:
            self._git(directory, "add", ".adam/evidence/obsolete.json")
        self._git(directory, "commit", "-m", "baseline")

        if delete_source:
            source.unlink()
        else:
            source.write_text(source_changed, encoding="utf-8")
        if remove_baseline_evidence:
            (directory / ".adam" / "evidence" / "obsolete.json").unlink()
        if include_evidence:
            evidence_dir = directory / ".adam" / "evidence"
            evidence_dir.mkdir(parents=True, exist_ok=True)
            evidence_payload = json.loads(EXAMPLE.read_text(encoding="utf-8"))
            if evidence_level is not None:
                evidence_payload["level"] = evidence_level
            if evidence_schema_version is not None:
                evidence_payload["schema_version"] = evidence_schema_version
            test_output = evidence_dir / "order-api-migration-tests.txt"
            typecheck_output = evidence_dir / "order-api-migration-typecheck.txt"
            review_output = evidence_dir / "order-api-migration-review.txt"
            test_output.write_text("tests passed\n", encoding="utf-8")
            typecheck_output.write_text("typecheck passed\n", encoding="utf-8")
            review_output.write_text("review approved\n", encoding="utf-8")
            evidence_payload["supporting_artifacts"][0]["sha256"] = hashlib.sha256(test_output.read_bytes()).hexdigest()
            evidence_payload["supporting_artifacts"][1]["sha256"] = hashlib.sha256(typecheck_output.read_bytes()).hexdigest()
            evidence_payload["supporting_artifacts"][2]["sha256"] = hashlib.sha256(review_output.read_bytes()).hexdigest()
            revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=directory, text=True).strip() + "+worktree"
            evidence_payload["supporting_artifacts"][0]["repository_revision"] = revision
            evidence_payload["supporting_artifacts"][1]["repository_revision"] = revision
            (evidence_dir / evidence_name).write_text(json.dumps(evidence_payload), encoding="utf-8")
        self._git(directory, "add", "-A")
        self._git(directory, "commit", "-m", "code change")
        return directory

    def _run_gate(
        self,
        directory: Path,
        *,
        evidence_dir: Path | None = None,
        require_level_two_for_high_risk: bool = False,
        include_working_tree: bool = False,
        base: str = "HEAD~1",
    ) -> subprocess.CompletedProcess[str]:
        command = [
            sys.executable,
            str(SCRIPTS / "check_change_evidence.py"),
            "--base",
            base,
            "--require-for-code-change",
        ]
        if evidence_dir is not None:
            command.extend(["--evidence-dir", str(evidence_dir)])
        if require_level_two_for_high_risk:
            command.append("--require-level-two-for-high-risk")
        if include_working_tree:
            command.append("--include-working-tree")
        return subprocess.run(
            command,
            cwd=directory,
            capture_output=True,
            text=True,
            check=False,
        )

    def _git(self, directory: Path, *args: str) -> None:
        subprocess.run(["git", *args], cwd=directory, check=True, capture_output=True)


if __name__ == "__main__":
    unittest.main()
