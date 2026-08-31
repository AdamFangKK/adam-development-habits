from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_development_events import validate_events  # noqa: E402


def event(name: str, *, classification: str = "not_applicable", outcome: str = "verified") -> dict[str, object]:
    return {
        "event": name,
        "change_id": "cleanup-demo",
        "component": "policy.evaluate",
        "outcome": outcome,
        "classification": classification,
        "evidence_id": "cleanup-tests",
        "duration_ms": 4,
        "labels": ["component", "operation", "outcome", "classification"],
    }


class DevelopmentEventTests(unittest.TestCase):
    def test_level_zero_rejects_accidental_telemetry(self) -> None:
        self.assertEqual(validate_events([], level=0), [])
        self.assertTrue(any("level 0" in error for error in validate_events([event("verified")], level=0)))

    def test_level_one_requires_checkpoints_and_accepts_bounded_events(self) -> None:
        events = [
            event("owner_located", classification="reuse_existing_owner", outcome="executed"),
            event("retirement_classified", classification="remove"),
            event("verification_completed"),
        ]
        self.assertEqual(validate_events(events, level=1), [])

    def test_level_two_requires_full_lifecycle(self) -> None:
        events = [event(name) for name in ("started", "owner_located", "implemented", "cleanup_classified", "verified", "committed")]
        self.assertEqual(validate_events(events, level=2), [])
        reversed_events = [event(name) for name in ("started", "implemented", "owner_located", "cleanup_classified", "verified", "committed")]
        self.assertTrue(any("must be ordered" in error for error in validate_events(reversed_events, level=2)))

    def test_cleanup_level_one_requires_documentation_and_orphan_checkpoints(self) -> None:
        events = [
            event(name, classification="remove" if name == "retirement_classified" else "not_applicable")
            for name in (
                "cleanup_started",
                "owner_located",
                "retirement_classified",
                "documentation_synchronized",
                "orphan_scan_completed",
                "verification_completed",
            )
        ]
        self.assertEqual(validate_events(events, level=1, cleanup=True), [])
        missing_docs = [item for item in events if item["event"] != "documentation_synchronized"]
        self.assertTrue(any("documentation_synchronized" in error for error in validate_events(missing_docs, level=1, cleanup=True)))

    def test_cleanup_level_two_rejects_out_of_order_or_incomplete_lifecycle(self) -> None:
        names = (
            "started",
            "owner_located",
            "implemented",
            "cleanup_started",
            "cleanup_classified",
            "documentation_synchronized",
            "orphan_scan_completed",
            "verified",
            "committed",
        )
        self.assertEqual(validate_events([event(name) for name in names], level=2, cleanup=True), [])
        reordered = [event(name) for name in (*names[:5], "orphan_scan_completed", "documentation_synchronized", *names[7:])]
        self.assertTrue(any("must be ordered" in error for error in validate_events(reordered, level=2, cleanup=True)))

    def test_cleanup_flag_does_not_change_level_zero_no_telemetry_rule(self) -> None:
        self.assertEqual(validate_events([], level=0, cleanup=True), [])
        self.assertTrue(validate_events([event("cleanup_started")], level=0, cleanup=True))

    def test_traps_reject_sensitive_fields_duplicate_transitions_and_unbounded_labels(self) -> None:
        events = [
            event("owner_located"),
            {**event("retirement_classified", classification="remove"), "raw_payload": "{""secret"": true}"},
            event("retirement_classified", classification="remove"),
            {**event("verification_completed"), "labels": ["a" * 33]},
        ]
        errors = validate_events(events, level=1)
        self.assertTrue(any("forbidden sensitive" in error for error in errors))
        self.assertTrue(any("duplicate logical transition" in error for error in errors))
        self.assertTrue(any("bounded snake_case" in error for error in errors))

    def test_cli_emits_machine_readable_result(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            lines = [event("owner_located", classification="reuse_existing_owner", outcome="executed"), event("retirement_classified", classification="remove"), event("verification_completed")]
            _ = path.write_text("".join(json.dumps(item) + "\n" for item in lines), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "validate_development_events.py"), "--events", str(path), "--level", "1"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = json.loads(result.stdout)
            self.assertTrue(report["valid"])
            self.assertEqual(report["event_count"], 3)

    def test_cli_cleanup_flag_enforces_cleanup_sequence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            lines = [
                event(name, classification="remove" if name == "retirement_classified" else "not_applicable")
                for name in (
                    "cleanup_started",
                    "owner_located",
                    "retirement_classified",
                    "documentation_synchronized",
                    "orphan_scan_completed",
                    "verification_completed",
                )
            ]
            _ = path.write_text("".join(json.dumps(item) + "\n" for item in lines), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "validate_development_events.py"),
                    "--events",
                    str(path),
                    "--level",
                    "1",
                    "--cleanup",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(json.loads(result.stdout)["valid"])


if __name__ == "__main__":
    _ = unittest.main()
