from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path
from typing import cast


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "examples" / "effect-experiment-native-v2"


def canonical_sha256(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class NativeCleanupEffectV2InvalidationTests(unittest.TestCase):
    def test_invalid_archives_bind_the_current_frozen_preregistration(self) -> None:
        for version in ("v2", "v3", "v4", "v5"):
            with self.subTest(version=version):
                experiment = ROOT / f"examples/effect-experiment-native-{version}"
                archive = cast(
                    dict[str, object], json.loads((experiment / "collection-invalid.json").read_text(encoding="utf-8"))
                )
                preregistration = cast(
                    dict[str, object], json.loads((experiment / "preregistration.json").read_text(encoding="utf-8"))
                )
                self.assertEqual(archive["preregistration_sha256"], canonical_sha256(preregistration))

    def test_partial_parallel_collection_stays_ineligible_and_complete_as_an_archive(self) -> None:
        record = cast(dict[str, object], json.loads((EXPERIMENT / "collection-invalid.json").read_text(encoding="utf-8")))
        self.assertEqual(record["status"], "ineligible")
        self.assertEqual(record["analysis_eligibility"], "ineligible")
        collection = cast(dict[str, object], record["collection"])
        self.assertEqual(collection["planned_trials"], 30)
        self.assertEqual(collection["completed_trials"], 3)
        self.assertIn("concurrently", cast(str, collection["observed_execution_deviation"]))
        raw_root = EXPERIMENT / "raw" / cast(str, collection["task_id"])
        conditions = ("old_skill", "new_skill", "no_skill")
        expected = {"prepare.json", "seed.txt", "candidate.diff", "agent-result.json", "score.json"}
        for condition in conditions:
            with self.subTest(condition=condition):
                trial = raw_root / condition
                self.assertEqual({path.name for path in trial.iterdir()}, expected)
                score = cast(dict[str, object], json.loads((trial / "score.json").read_text(encoding="utf-8")))
                self.assertTrue(score["implementation_integrity_passed"])
                self.assertTrue(cast(dict[str, object], score["public_result"])["passed"])
                self.assertTrue(score["hidden_injected_after_agent_exit"])
        self.assertEqual(
            cast(dict[str, object], record["observed_hidden_passes_diagnostic_only"]),
            {"no_skill": False, "old_skill": False, "new_skill": True},
        )
        self.assertEqual(record["causal_conclusion"], "unknown")


if __name__ == "__main__":
    _ = unittest.main()
