"""Regression tests for V8's isolated collection boundary."""

# pyright: reportMissingTypeStubs=false
# pyright: reportPrivateLocalImportUsage=false

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import cast
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import audit_effect_isolation_v8 as audit  # noqa: E402
import codex_v8_isolated as wrapper  # noqa: E402
import run_effect_experiment_v6 as v6  # noqa: E402
import run_effect_experiment_v8 as v8  # noqa: E402


def write_json(path: Path, value: dict[str, object]) -> None:
    _ = path.write_text(json.dumps(value), encoding="utf-8")


class EffectRunnerV8Tests(unittest.TestCase):
    def test_wrapper_injects_skill_search_disable_once(self) -> None:
        self.assertEqual(
            wrapper.inject_skill_search_disable(["exec", "-C", "/tmp/work", "prompt"]),
            ["exec", "--disable", "skill_search", "-C", "/tmp/work", "prompt"],
        )
        self.assertEqual(
            wrapper.inject_skill_search_disable(["exec", "--disable", "skill_search", "prompt"]),
            ["exec", "--disable", "skill_search", "prompt"],
        )

    def test_wrapper_executes_codex_with_the_isolation_flag(self) -> None:
        with patch.object(wrapper.shutil, "which", return_value="/usr/local/bin/codex"), patch.object(
            wrapper.os,
            "execv",
            side_effect=SystemExit(0),
        ) as execute, patch.object(sys, "argv", ["wrapper", "exec", "-C", "/tmp/work", "repair"]):
            with self.assertRaises(SystemExit):
                _ = wrapper.main()
        execute.assert_called_once_with(
            "/usr/local/bin/codex",
            ["/usr/local/bin/codex", "exec", "--disable", "skill_search", "-C", "/tmp/work", "repair"],
        )

    def test_v8_normalizes_experiment_artifact_paths(self) -> None:
        arguments = [
            "--corpus", "examples/corpus", "--prompts", "examples/prompts", "--skill", "SKILL.md",
            "--preregistration", "examples/preregistration.json", "--raw-output", "tmp/raw", "--output", "tmp/result.json",
        ]
        normalized = v8.normalize_path_arguments(arguments)
        for index, value in enumerate(normalized[:-1]):
            if value in {"--corpus", "--prompts", "--skill", "--preregistration", "--raw-output", "--output"}:
                self.assertTrue(Path(normalized[index + 1]).is_absolute())

    def test_v8_main_binds_versioned_scorer_only_while_running(self) -> None:
        original_score = v6.score_candidate
        original_model = v6.DEFAULT_MODEL_ID
        original_harness = v6.DEFAULT_HARNESS_ID
        seen: list[bool] = []

        def fake_main() -> int:
            seen.append(v6.score_candidate is v8.score_candidate)
            output_index = sys.argv.index("--output") + 1
            _ = Path(sys.argv[output_index]).write_text(json.dumps({"collection": {}}), encoding="utf-8")
            return 0

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "output.json"
            with patch.object(v8.protocol, "main", side_effect=fake_main), patch.object(v8.isolation, "audit_collection", return_value={"passed": True, "failures": []}), patch.object(sys, "argv", [
                "runner", "--corpus", str(root / "corpus"), "--prompts", str(root / "prompts"), "--skill", str(root / "SKILL.md"),
                "--preregistration", str(root / "preregistration.json"), "--raw-output", str(root / "raw"), "--output", str(output),
            ]):
                self.assertEqual(v8.main(), 0)
            recorded = cast(dict[str, object], json.loads(output.read_text(encoding="utf-8")))
            self.assertTrue(bool(cast(dict[str, object], recorded["collection"])["isolation_audit_passed"]))
        self.assertEqual(seen, [True])
        self.assertIs(v6.score_candidate, original_score)
        self.assertEqual(v6.DEFAULT_MODEL_ID, original_model)
        self.assertEqual(v6.DEFAULT_HARNESS_ID, original_harness)

    def test_audit_requires_actual_snapshot_read_and_wrapper_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = root / "raw"
            snapshot = root / "snapshot" / "SKILL.md"
            snapshot.parent.mkdir()
            _ = snapshot.write_text("# skill\n", encoding="utf-8")
            source = root / "global" / "SKILL.md"
            source.parent.mkdir()
            _ = source.write_text("# source\n", encoding="utf-8")
            trials: list[dict[str, object]] = []
            for condition in ("baseline", "skill"):
                artifact = raw / "task" / condition
                artifact.mkdir(parents=True)
                _ = (artifact / "agent-output.md").write_text("done\n", encoding="utf-8")
                log = audit.ISOLATION_MARKER + "\n"
                if condition == "skill":
                    log += f"The supplied Skill path is: {snapshot}.\nexec\n/bin/zsh -lc 'sed -n 1p {snapshot}'\n"
                _ = (artifact / "agent.stderr.log").write_text(log, encoding="utf-8")
                trials.append({"condition": condition, "artifact_path": f"task/{condition}"})
            result = root / "result.json"
            write_json(result, {"trials": trials})
            report = audit.audit_collection(raw, result, source)
            self.assertTrue(report["passed"], report)

            skill_log = raw / "task" / "skill" / "agent.stderr.log"
            _ = skill_log.write_text(audit.ISOLATION_MARKER + f"\nThe supplied Skill path is: {snapshot}.\n", encoding="utf-8")
            rejected = audit.audit_collection(raw, result, source)
            self.assertFalse(rejected["passed"])
            self.assertIn("treatment did not read", "\n".join(cast(list[str], rejected["failures"])))

            _ = skill_log.write_text(
                audit.ISOLATION_MARKER
                + f"\nThe supplied Skill path is: {snapshot}.\nexec\n/bin/zsh -lc 'sed -n 1p {snapshot}'\n"
                + f"exec\n/bin/zsh -lc 'sed -n 1p {source}'\n",
                encoding="utf-8",
            )
            contaminated = audit.audit_collection(raw, result, source)
            self.assertFalse(contaminated["passed"])
            self.assertIn("globally available", "\n".join(cast(list[str], contaminated["failures"])))


if __name__ == "__main__":
    _ = unittest.main()
