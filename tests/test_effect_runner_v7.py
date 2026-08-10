from __future__ import annotations

# pyright: reportMissingTypeStubs=false
# pyright: reportPrivateLocalImportUsage=false

import hashlib
import json
import sys
import unittest
from pathlib import Path
from typing import cast
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import run_effect_experiment_v6 as v6  # noqa: E402
import run_effect_experiment_v7 as v7  # noqa: E402
from analyze_skill_effect import analyze_experiment, canonical_sha256, immutable_envelope  # noqa: E402


def load_object(path: Path) -> dict[str, object]:
    value = cast(object, json.loads(path.read_text(encoding="utf-8")))
    if not isinstance(value, dict):
        raise AssertionError(f"{path} must contain a JSON object")
    return cast(dict[str, object], value)


class EffectRunnerV7Tests(unittest.TestCase):
    def test_v7_entry_points_are_versioned_and_do_not_patch_v6_at_import(self) -> None:
        self.assertIn("checkpointed-v7", v7.DEFAULT_HARNESS_ID)
        self.assertEqual(v6.DEFAULT_HARNESS_ID, "codex-cli-0.146.0-alpha.9.2;exec;workspace-write;ephemeral;checkpointed-v6")
        self.assertNotEqual(
            hashlib.sha256((SCRIPTS / "run_effect_experiment_v7.py").read_bytes()).hexdigest(),
            hashlib.sha256((SCRIPTS / "run_effect_experiment_v6.py").read_bytes()).hexdigest(),
        )
        self.assertNotEqual(
            hashlib.sha256((SCRIPTS / "score_effect_workspace_v7.py").read_bytes()).hexdigest(),
            hashlib.sha256((SCRIPTS / "score_effect_workspace_v6.py").read_bytes()).hexdigest(),
        )

    def test_v7_main_restores_v6_bindings_after_delegation(self) -> None:
        original_score_candidate = v6.score_candidate
        original_model_id = v6.DEFAULT_MODEL_ID
        original_harness_id = v6.DEFAULT_HARNESS_ID
        with patch.object(v7.protocol, "main", return_value=0):
            self.assertEqual(v7.main(), 0)
        self.assertIs(v6.score_candidate, original_score_candidate)
        self.assertEqual(v6.DEFAULT_MODEL_ID, original_model_id)
        self.assertEqual(v6.DEFAULT_HARNESS_ID, original_harness_id)

    def test_v7_preregistration_freezes_the_complete_fresh_corpus(self) -> None:
        preregistration = load_object(ROOT / "examples" / "effect-experiment-v7" / "preregistration.json")
        manifest = load_object(ROOT / "examples" / "effect-corpus-v7" / "manifest.json")
        protocol = cast(dict[str, object], preregistration["protocol"])
        preregistration_meta = cast(dict[str, object], preregistration["preregistration"])
        report = analyze_experiment(preregistration)

        self.assertEqual(report["conclusion"], "not_run: this preregistration is a protocol, not evidence that the Skill improves a model.")
        self.assertEqual(preregistration["status"], "planned")
        self.assertEqual(preregistration["trials"], [])
        self.assertEqual(protocol["runner_sha256"], hashlib.sha256((SCRIPTS / "run_effect_experiment_v7.py").read_bytes()).hexdigest())
        self.assertEqual(protocol["base_runner_sha256"], hashlib.sha256((SCRIPTS / "run_effect_experiment_v6.py").read_bytes()).hexdigest())
        self.assertEqual(protocol["hidden_scorer_sha256"], hashlib.sha256((SCRIPTS / "score_effect_workspace_v7.py").read_bytes()).hexdigest())
        self.assertEqual(protocol["base_hidden_scorer_sha256"], hashlib.sha256((SCRIPTS / "score_effect_workspace_v6.py").read_bytes()).hexdigest())
        self.assertEqual(preregistration_meta["protocol_sha256"], canonical_sha256(protocol))
        self.assertEqual(preregistration_meta["envelope_sha256"], canonical_sha256(immutable_envelope(preregistration)))

        records = v6.records_for_preregistration(manifest, preregistration)
        self.assertEqual(len(records), 20)
        self.assertEqual({record.stratum for record in records}, {"single-module", "cross-module", "integration"})


if __name__ == "__main__":
    _ = unittest.main()
