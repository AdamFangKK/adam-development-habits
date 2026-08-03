from __future__ import annotations

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
sys.path.insert(0, str(SCRIPTS))

from validate_evidence import validate_evidence  # noqa: E402


class EvidenceScriptTests(unittest.TestCase):
    def test_example_is_valid(self) -> None:
        payload = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        self.assertEqual(validate_evidence(payload), [])

    def test_level_two_requires_independent_review(self) -> None:
        payload = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        del payload["independent_review"]
        self.assertIn("independent_review must be an object for level 2", validate_evidence(payload))

    def test_level_two_requires_approved_review(self) -> None:
        payload = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        payload["independent_review"]["outcome"] = "changes_requested"
        self.assertIn("independent_review.outcome must be approved", validate_evidence(payload))

    def test_evidence_requires_a_real_verification(self) -> None:
        payload = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        for verification in payload["verification"]:
            verification["status"] = "not_applicable"
        self.assertIn("verification must contain at least one passed result", validate_evidence(payload))

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

    def test_documentation_configuration_does_not_require_evidence(self) -> None:
        directory = self._make_repository(include_evidence=False, source_name="docs/example.yaml")
        result = self._run_gate(directory)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("no behavior-changing files changed", result.stdout)

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

    def _make_repository(
        self,
        *,
        include_evidence: bool,
        delete_source: bool = False,
        source_name: str = "app.py",
        baseline_evidence: bool = False,
        evidence_name: str = "order-api-migration.json",
        remove_baseline_evidence: bool = False,
    ) -> Path:
        directory = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, directory, True)
        self._git(directory, "init")
        self._git(directory, "config", "user.name", "Evidence Test")
        self._git(directory, "config", "user.email", "evidence-test@example.invalid")
        source = directory / source_name
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("VALUE = 1\n", encoding="utf-8")
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
            source.write_text("VALUE = 2\n", encoding="utf-8")
        if remove_baseline_evidence:
            (directory / ".adam" / "evidence" / "obsolete.json").unlink()
        if include_evidence:
            evidence_dir = directory / ".adam" / "evidence"
            evidence_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy(EXAMPLE, evidence_dir / evidence_name)
        self._git(directory, "add", "-A")
        self._git(directory, "commit", "-m", "code change")
        return directory

    def _run_gate(self, directory: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "check_change_evidence.py"),
                "--base",
                "HEAD~1",
                "--require-for-code-change",
            ],
            cwd=directory,
            capture_output=True,
            text=True,
            check=False,
        )

    def _git(self, directory: Path, *args: str) -> None:
        subprocess.run(["git", *args], cwd=directory, check=True, capture_output=True)


if __name__ == "__main__":
    unittest.main()
