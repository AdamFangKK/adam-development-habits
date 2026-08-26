from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import cast


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
MANIFEST = ROOT / "examples" / "external-click-run-manifest.json"
REPLAY = ROOT / "examples" / "external-click-replay.json"
EVIDENCE = ROOT / ".adam" / "evidence" / "external-click-replay.json"
sys.path.insert(0, str(SCRIPTS))

from replay_external_click import (  # noqa: E402
    BUGGY_REVISION,
    CHECK_TIMEOUT_SECONDS,
    EXPECTED_TREES,
    EXPECTED_TYPES,
    PATCH_REVISION,
    require_symlink_support,
    replace_once,
    source_root,
    test_environment as run_test_environment,
)
from validate_evidence import validate_evidence  # noqa: E402


def load_object(path: Path) -> dict[str, object]:
    value = cast(object, json.loads(path.read_text(encoding="utf-8")))
    if not isinstance(value, dict):
        raise AssertionError(f"{path} must contain a JSON object")
    return cast(dict[str, object], value)


def require_object(value: object, name: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise AssertionError(f"{name} must be an object")
    return cast(dict[str, object], value)


def require_text(value: object, name: str) -> str:
    if not isinstance(value, str):
        raise AssertionError(f"{name} must be text")
    return value


def require_bool(value: object, name: str) -> bool:
    if not isinstance(value, bool):
        raise AssertionError(f"{name} must be boolean")
    return value


class ExternalClickReplayTests(unittest.TestCase):
    def test_manifest_pins_the_upstream_revisions_and_provenance(self) -> None:
        manifest = load_object(MANIFEST)
        source = require_object(manifest["source"], "source")
        materialization = require_object(manifest["materialization"], "materialization")
        protocol = require_object(manifest["protocol"], "protocol")
        self.assertEqual(require_text(source["buggy_revision"], "buggy revision"), BUGGY_REVISION)
        self.assertEqual(require_text(source["official_patch_revision"], "official patch"), PATCH_REVISION)
        self.assertEqual(require_text(source["buggy_click_tree_sha256"], "buggy tree"), EXPECTED_TREES["buggy"])
        self.assertEqual(require_text(source["official_patch_click_tree_sha256"], "patch tree"), EXPECTED_TREES["patch"])
        self.assertEqual(require_text(source["buggy_types_sha256"], "buggy types"), EXPECTED_TYPES["buggy"])
        self.assertEqual(require_text(source["official_patch_types_sha256"], "patch types"), EXPECTED_TYPES["patch"])
        self.assertIn("no network access", require_text(materialization["runner_behavior"], "runner behavior"))
        self.assertIn("partial-repair", require_object(protocol["variants"], "variants"))

    def test_saved_replay_reports_the_expected_adversarial_outcomes(self) -> None:
        report = load_object(REPLAY)
        source = require_object(report["source"], "source")
        tool = require_object(report["tool"], "tool")
        variants = require_object(report["variants"], "variants")
        conclusion = require_object(report["conclusion"], "conclusion")
        self.assertEqual(require_text(source["buggy_revision"], "buggy revision"), BUGGY_REVISION)
        self.assertEqual(require_text(source["official_patch_revision"], "official patch"), PATCH_REVISION)
        self.assertEqual(require_text(tool["sha256"], "tool hash"), hashlib.sha256((SCRIPTS / "replay_external_click.py").read_bytes()).hexdigest())
        self.assertTrue(require_bool(conclusion["protocol_effective"], "protocol effective"))

        expected = {
            "buggy-8.0.1": (False, False),
            "partial-repair": (True, False),
            "official-owner-patch": (True, True),
            "official-patch": (True, True),
        }
        for label, (public_passed, hidden_passed) in expected.items():
            with self.subTest(label=label):
                result = require_object(variants[label], label)
                public = require_object(result["public"], f"{label} public")
                hidden = require_object(result["hidden"], f"{label} hidden")
                self.assertEqual(require_bool(public["passed"], f"{label} public passed"), public_passed)
                self.assertEqual(require_bool(hidden["passed"], f"{label} hidden passed"), hidden_passed)

    def test_source_validation_rejects_an_unpinned_tree(self) -> None:
        with tempfile.TemporaryDirectory(prefix="adam-click-invalid-") as temporary_directory:
            root = Path(temporary_directory)
            types_path = root / "src" / "click" / "types.py"
            types_path.parent.mkdir(parents=True)
            _ = types_path.write_text("# not Click\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "source tree SHA-256"):
                _ = source_root(root, "buggy")

    def test_patch_application_requires_one_unambiguous_causal_owner_match(self) -> None:
        with self.assertRaisesRegex(ValueError, "exactly once"):
            _ = replace_once("no matching owner", "missing", "replacement", "test patch")
        with self.assertRaisesRegex(ValueError, "exactly once"):
            _ = replace_once("old old", "old", "new", "test patch")

    def test_current_platform_satisfies_the_declared_symlink_prerequisite(self) -> None:
        require_symlink_support()

    def test_test_subprocess_sees_only_the_copied_click_package(self) -> None:
        with tempfile.TemporaryDirectory(prefix="adam-click-isolation-") as temporary_directory:
            root = Path(temporary_directory)
            click_init = root / "src" / "click" / "__init__.py"
            click_init.parent.mkdir(parents=True)
            _ = click_init.write_text("VALUE = 'verified'\n", encoding="utf-8")
            _ = (root / "src" / "sitecustomize.py").write_text("raise RuntimeError('untrusted source root')\n", encoding="utf-8")
            result = run_test_environment(root, "import click; assert click.VALUE == 'verified'")
            self.assertTrue(result["passed"], result["summary"])

    def test_test_subprocess_has_a_bounded_timeout(self) -> None:
        with tempfile.TemporaryDirectory(prefix="adam-click-timeout-") as temporary_directory:
            root = Path(temporary_directory)
            click_init = root / "src" / "click" / "__init__.py"
            click_init.parent.mkdir(parents=True)
            _ = click_init.write_text("", encoding="utf-8")
            result = run_test_environment(root, "import time; time.sleep(1)", timeout_seconds=0.01)
            self.assertEqual(result["exit_code"], 124)
            self.assertIn("timed out", result["summary"])
            self.assertGreater(CHECK_TIMEOUT_SECONDS, 0)

    def test_report_declares_the_real_limit_of_the_claim(self) -> None:
        report = load_object(REPLAY)
        conclusion = require_object(report["conclusion"], "conclusion")
        self.assertIn("does not estimate model repair-success uplift", require_text(conclusion["not_proven"], "not proven"))

    def test_level_two_evidence_is_hash_linked_and_valid(self) -> None:
        evidence = load_object(EVIDENCE)
        self.assertEqual(
            validate_evidence(evidence, expected_change_id="external-click-replay", artifact_root=ROOT),
            [],
        )


if __name__ == "__main__":
    _ = unittest.main()
