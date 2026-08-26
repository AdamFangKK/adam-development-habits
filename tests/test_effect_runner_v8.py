"""Regression tests for V8's isolated collection boundary."""

# pyright: reportMissingTypeStubs=false
# pyright: reportPrivateLocalImportUsage=false

from __future__ import annotations

import json
import hashlib
import subprocess
import sys
import tempfile
import unittest
from contextlib import nullcontext
from pathlib import Path
from typing import cast
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
V8_PREREGISTRATION_COMMIT = "3c838583edd7ebac2d0d0b47f405a7d45b462b2b"
sys.path.insert(0, str(SCRIPTS))

import audit_effect_isolation_v8 as audit  # noqa: E402
import codex_v8_isolated as wrapper  # noqa: E402
import run_effect_experiment_v6 as v6  # noqa: E402
import run_effect_experiment_v8 as v8  # noqa: E402


def write_json(path: Path, value: dict[str, object]) -> None:
    _ = path.write_text(json.dumps(value), encoding="utf-8")


def load_json(path: Path) -> dict[str, object]:
    value = cast(object, json.loads(path.read_text(encoding="utf-8")))
    if not isinstance(value, dict):
        raise AssertionError(f"{path} must contain a JSON object")
    return cast(dict[str, object], value)


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
        normalized = v8.v8_arguments(arguments)
        for index, value in enumerate(normalized[:-1]):
            if value in {"--corpus", "--prompts", "--skill", "--preregistration", "--raw-output", "--output"}:
                self.assertTrue(Path(normalized[index + 1]).is_absolute())
        self.assertEqual(normalized[normalized.index("--agent-timeout") + 1], str(v8.DEFAULT_AGENT_TIMEOUT_SECONDS))
        self.assertEqual(normalized[normalized.index("--test-timeout") + 1], str(v8.DEFAULT_TEST_TIMEOUT_SECONDS))

    def test_v8_rejects_argparse_aliases_equals_forms_and_duplicates(self) -> None:
        for arguments in (
            ["--mo", "gpt-5.6-terra"],
            ["--model=gpt-5.6-terra"],
            ["--agent-t=420"],
            ["--model", "gpt-5.6-terra", "--model", "other"],
            ["--unknown-option"],
        ):
            with self.assertRaisesRegex(ValueError, "option|must appear"):
                v8.validate_option_spelling(arguments)
        v8.validate_option_spelling(["--model", "gpt-5.6-terra", "--preflight"])

    def test_v8_rejects_seed_and_timeout_drift_before_delegating(self) -> None:
        preregistration = ROOT / "examples" / "effect-experiment-v8" / "preregistration.json"
        record = cast(dict[str, object], json.loads(preregistration.read_text(encoding="utf-8")))
        base = [
            "--preregistration", str(preregistration), "--seed", "20260812",
            "--agent-timeout", str(v8.DEFAULT_AGENT_TIMEOUT_SECONDS),
            "--test-timeout", str(v8.DEFAULT_TEST_TIMEOUT_SECONDS),
        ]
        v8.validate_frozen_budget(record, base)

        for option, replacement, message in (
            ("--seed", "1", "random_seed"),
            ("--agent-timeout", "1", "agent_timeout_seconds"),
            ("--test-timeout", "1", "test_timeout_seconds"),
        ):
            changed = list(base)
            changed[changed.index(option) + 1] = replacement
            with self.assertRaisesRegex(ValueError, message):
                v8.validate_frozen_budget(record, changed)

    def test_v8_rejects_runtime_input_or_output_reuse(self) -> None:
        preregistration_path = ROOT / "examples" / "effect-experiment-v8" / "preregistration.json"
        preregistration = cast(dict[str, object], json.loads(preregistration_path.read_text(encoding="utf-8")))
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory)
            frozen = root / "frozen"
            frozen.mkdir()
            v8.copy_frozen_archive(ROOT, V8_PREREGISTRATION_COMMIT, frozen)
            raw = root / "raw"
            output = root / "result.json"
            arguments = [
                "--corpus", str(frozen / "examples" / "effect-corpus-v8"),
                "--prompts", str(frozen / "examples" / "effect-experiment-v7" / "prompts"),
                "--skill", str(frozen),
                "--codex", str(frozen / "scripts" / "codex_v8_isolated.py"),
                "--raw-output", str(raw),
                "--output", str(output),
            ]
            v8.validate_bound_inputs(preregistration, arguments)
            v8.validate_empty_collection_outputs(arguments)

            live_skill = list(arguments)
            live_skill[live_skill.index("--skill") + 1] = str(ROOT)
            with self.assertRaisesRegex(ValueError, "Skill source differs"):
                v8.validate_bound_inputs(preregistration, live_skill)

            raw.mkdir()
            _ = (raw / "old-artifact").write_text("old\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "raw-output"):
                v8.validate_empty_collection_outputs(arguments)

            _ = (raw / "old-artifact").unlink()
            _ = output.write_text("old\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "--output"):
                v8.validate_empty_collection_outputs(arguments)

            changed = list(arguments)
            changed[changed.index("--prompts") + 1] = str(frozen / "examples" / "effect-experiment-v8")
            with self.assertRaisesRegex(ValueError, "baseline prompt"):
                v8.validate_bound_inputs(preregistration, changed)

            symlink_target = root / "safe-output"
            symlink_target.mkdir()
            raw_link = root / "raw-link"
            raw_link.symlink_to(symlink_target, target_is_directory=True)
            linked = list(arguments)
            linked[linked.index("--raw-output") + 1] = str(raw_link)
            with self.assertRaisesRegex(ValueError, "symbolic[- ]link"):
                v8.validate_empty_collection_outputs(linked)

            raw_parent_link = root / "raw-parent-link"
            raw_parent_link.symlink_to(symlink_target, target_is_directory=True)
            raw_parent_linked = list(arguments)
            raw_parent_linked[raw_parent_linked.index("--raw-output") + 1] = str(raw_parent_link / "raw")
            with self.assertRaisesRegex(ValueError, "symbolic-link path component"):
                v8.validate_empty_collection_outputs(raw_parent_linked)

            output.unlink()
            output_parent_link = root / "output-parent-link"
            output_parent_link.symlink_to(raw, target_is_directory=True)
            output_parent_linked = list(arguments)
            output_parent_linked[output_parent_linked.index("--output") + 1] = str(output_parent_link / "result.json")
            with self.assertRaisesRegex(ValueError, "symbolic-link path component"):
                v8.validate_empty_collection_outputs(output_parent_linked)

    def test_v8_rejects_empty_corpus_tree_and_invalid_envelope(self) -> None:
        preregistration_path = ROOT / "examples" / "effect-experiment-v8" / "preregistration.json"
        preregistration = cast(dict[str, object], json.loads(preregistration_path.read_text(encoding="utf-8")))
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory)
            corpus = root / "corpus"
            corpus.mkdir()
            manifest = ROOT / "examples" / "effect-corpus-v8" / "manifest.json"
            _ = (corpus / "manifest.json").write_bytes(manifest.read_bytes())
            with self.assertRaisesRegex(ValueError, "workspace is missing"):
                v8.validate_corpus_trees(corpus, preregistration)

        invalid = cast(dict[str, object], json.loads(json.dumps(preregistration)))
        metadata = cast(dict[str, object], invalid["preregistration"])
        metadata["protocol_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "protocol_sha256"):
            v8.validate_planned_envelope(invalid, ["--model", v8.DEFAULT_MODEL_ID, "--harness", v8.DEFAULT_HARNESS_ID])

    def test_v8_rejects_corpus_directory_symlink_even_when_file_hashes_match(self) -> None:
        preregistration = load_json(ROOT / "examples" / "effect-experiment-v8" / "preregistration.json")
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory)
            corpus = root / "corpus"
            corpus.mkdir()
            target = root / "external"
            target.mkdir()
            (corpus / "linked-directory").symlink_to(target, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "symbolic links"):
                v8.validate_corpus_trees(corpus, preregistration)

    def test_v8_implementation_hash_includes_analyzer(self) -> None:
        preregistration = cast(dict[str, object], json.loads((ROOT / "examples" / "effect-experiment-v8" / "preregistration.json").read_text(encoding="utf-8")))
        protocol = cast(dict[str, object], preregistration["protocol"])
        mutated = cast(dict[str, object], json.loads(json.dumps(preregistration)))
        mutated_protocol = cast(dict[str, object], mutated["protocol"])
        mutated_protocol["runner_sha256"] = hashlib.sha256((SCRIPTS / "run_effect_experiment_v8.py").read_bytes()).hexdigest()
        self.assertEqual(protocol["analyzer_sha256"], hashlib.sha256((SCRIPTS / "analyze_skill_effect.py").read_bytes()).hexdigest())
        mutated_protocol["analyzer_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "analyzer"):
            v8.validate_frozen_implementation(mutated)
        mutated_protocol["analyzer_sha256"] = protocol["analyzer_sha256"]
        mutated_protocol["execution_inputs_archived_from_preregistration_commit"] = False
        with self.assertRaisesRegex(ValueError, "execution_inputs_archived"):
            v8.validate_frozen_implementation(mutated)

    def test_v8_rejects_unexpected_codex_version_and_unsafe_output_layout(self) -> None:
        successful = subprocess.CompletedProcess(["codex", "--version"], 0, f"codex-cli {v8.CODEX_VERSION}\n", "")
        with patch.object(v8.shutil, "which", return_value="/usr/local/bin/codex"), patch.object(v8.subprocess, "run", return_value=successful):
            v8.validate_codex_version()
        wrong = subprocess.CompletedProcess(["codex", "--version"], 0, "codex-cli 9.9.9\n", "")
        with patch.object(v8.shutil, "which", return_value="/usr/local/bin/codex"), patch.object(v8.subprocess, "run", return_value=wrong):
            with self.assertRaisesRegex(ValueError, "version differs"):
                v8.validate_codex_version()

        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory)
            arguments = ["--raw-output", str(root / "raw"), "--output", str(root / "raw" / "result.json")]
            with self.assertRaisesRegex(ValueError, "outside"):
                v8.validate_empty_collection_outputs(arguments)

    def test_v8_requires_committed_preregistration_bytes(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory)
            preregistration = root / "preregistration.json"
            _ = preregistration.write_text('{"status":"planned"}\n', encoding="utf-8")
            for command in (
                ["git", "init", "-q", str(root)],
                ["git", "-C", str(root), "config", "user.email", "tests@example.invalid"],
                ["git", "-C", str(root), "config", "user.name", "V8 test"],
                ["git", "-C", str(root), "add", "preregistration.json"],
                ["git", "-C", str(root), "commit", "-qm", "freeze preregistration"],
            ):
                _ = subprocess.run(command, check=True, capture_output=True)
            commit = subprocess.run(
                ["git", "-C", str(root), "rev-parse", "HEAD"], check=True, capture_output=True, text=True
            ).stdout.strip()
            v8.validate_preregistration_commit(preregistration, commit)

            _ = preregistration.write_text('{"status":"changed"}\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "differs"):
                v8.validate_preregistration_commit(preregistration, commit)

    def test_v8_preflight_stops_before_delegated_runner(self) -> None:
        def no_runtime_load() -> object:
            raise AssertionError("runtime modules must not load during preflight")

        with patch.object(v8, "validate_frozen_run_arguments") as validate, patch.object(v8, "load_runtime_modules", side_effect=no_runtime_load), patch.object(sys, "argv", [
            "runner", "--preflight",
        ]):
            self.assertEqual(v8.main(), 0)
        validate.assert_called_once()

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

        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory)
            output = root / "output.json"
            isolation = type("Isolation", (), {"audit_collection": staticmethod(lambda *_: {"passed": True, "failures": []})})
            staged = v8.FrozenExecution(
                arguments=[
                    "--corpus", str(root / "corpus"), "--prompts", str(root / "prompts"), "--skill", str(root / "SKILL.md"),
                    "--preregistration", str(root / "preregistration.json"), "--raw-output", str(root / "raw"), "--output", str(output), "--seed", "20260812",
                ],
                script_root=SCRIPTS,
            )
            with patch.object(v8, "load_runtime_modules", return_value=(v6, isolation)), patch.object(v8, "frozen_execution", return_value=nullcontext(staged)), patch.object(v6, "main", side_effect=fake_main), patch.object(v8, "validate_frozen_run_arguments") as validate, patch.object(sys, "argv", [
                "runner", "--corpus", str(root / "corpus"), "--prompts", str(root / "prompts"), "--skill", str(root / "SKILL.md"),
                "--preregistration", str(root / "preregistration.json"), "--raw-output", str(root / "raw"), "--output", str(output), "--seed", "20260812",
            ]):
                self.assertEqual(v8.main(), 0)
            validate.assert_called_once()
            recorded = cast(dict[str, object], json.loads(output.read_text(encoding="utf-8")))
            self.assertTrue(bool(cast(dict[str, object], recorded["collection"])["isolation_audit_passed"]))
        self.assertEqual(seen, [True])
        self.assertIs(v6.score_candidate, original_score)
        self.assertEqual(v6.DEFAULT_MODEL_ID, original_model)
        self.assertEqual(v6.DEFAULT_HARNESS_ID, original_harness)

    def test_v8_hidden_scorer_reuses_the_staged_runtime_without_live_reload(self) -> None:
        class FrozenRuntime:
            def environment(self) -> dict[str, str]:
                return {"V8_FROZEN_RUNTIME": "1"}

        class FrozenTask:
            def __init__(self) -> None:
                self.hidden_root_path: str = "hidden/task"
                self.hidden_command: tuple[str, ...] = ("python3", "-m", "unittest")

        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory)
            staged_scripts = root / "archive" / "scripts"
            run_root = root / "candidate"
            corpus = root / "corpus"
            task = FrozenTask()
            completed = subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout='{"passed": true}\n',
                stderr="",
            )
            with patch.object(v8, "_runtime_protocol", FrozenRuntime()), patch.object(
                v8, "_runtime_script_root", staged_scripts
            ), patch.object(
                v8, "load_runtime_modules", side_effect=AssertionError("live runtime reload is forbidden")
            ) as load, patch.object(v8.subprocess, "run", return_value=completed) as run:
                report = v8.score_candidate(run_root=run_root, task=task, corpus=corpus, timeout=30.0)

        self.assertTrue(bool(report["passed"]))
        load.assert_not_called()
        command = cast(list[str], run.call_args.args[0])
        self.assertEqual(command[1], str(staged_scripts / "score_effect_workspace_v8.py"))
        self.assertEqual(run.call_args.kwargs["env"], {"V8_FROZEN_RUNTIME": "1"})

    def test_v8_frozen_worktree_rejects_dirty_or_external_inputs(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory)
            corpus = root / "corpus"
            prompts = root / "prompts"
            skill = root / "SKILL.md"
            wrapper = root / "scripts" / "run_effect_experiment_v8.py"
            preregistration = root / "preregistration.json"
            for path in (corpus, prompts, wrapper.parent):
                path.mkdir()
            _ = (corpus / "manifest.json").write_text("{}\n", encoding="utf-8")
            _ = (prompts / "baseline.txt").write_text("baseline\n", encoding="utf-8")
            _ = (prompts / "skill.txt").write_text("skill\n", encoding="utf-8")
            _ = skill.write_text("# Skill\n", encoding="utf-8")
            _ = wrapper.write_text("# wrapper\n", encoding="utf-8")
            _ = preregistration.write_text("{}\n", encoding="utf-8")
            for command in (
                ["git", "init", "-q", str(root)],
                ["git", "-C", str(root), "config", "user.email", "tests@example.invalid"],
                ["git", "-C", str(root), "config", "user.name", "V8 test"],
                ["git", "-C", str(root), "add", "."],
                ["git", "-C", str(root), "commit", "-qm", "freeze inputs"],
            ):
                _ = subprocess.run(command, check=True, capture_output=True)
            commit = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
            arguments = [
                "--corpus", str(corpus), "--prompts", str(prompts), "--skill", str(skill), "--codex", str(wrapper),
                "--preregistration", str(preregistration), "--raw-output", str(root / "raw"), "--output", str(root / "result.json"),
            ]
            with patch.object(v8, "__file__", str(wrapper)):
                self.assertEqual(v8.validate_frozen_worktree(preregistration, commit, arguments), root.resolve())

            _created = (root / "untracked-input").write_text("drift\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "clean"):
                with patch.object(v8, "__file__", str(wrapper)):
                    _ = v8.validate_frozen_worktree(preregistration, commit, arguments)
            (root / "untracked-input").unlink()

            outside = Path(directory).parent / "outside-v8-input"
            _created = outside.write_text("outside\n", encoding="utf-8")
            external = list(arguments)
            external[external.index("--skill") + 1] = str(outside)
            with self.assertRaisesRegex(ValueError, "inside"):
                with patch.object(v8, "__file__", str(wrapper)):
                    _ = v8.validate_frozen_worktree(preregistration, commit, external)
            outside.unlink()

    def test_v8_staged_execution_reads_committed_bytes_after_live_input_changes(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory)
            corpus = root / "corpus"
            prompts = root / "prompts"
            scripts = root / "scripts"
            skill = root / "SKILL.md"
            preregistration = root / "preregistration.json"
            wrapper = scripts / "codex_v8_isolated.py"
            runner = scripts / "run_effect_experiment_v8.py"
            for path in (corpus, prompts, scripts):
                path.mkdir()
            _ = (corpus / "manifest.json").write_text("{}\n", encoding="utf-8")
            _ = (prompts / "baseline.txt").write_text("baseline\n", encoding="utf-8")
            _ = (prompts / "skill.txt").write_text("skill\n", encoding="utf-8")
            _ = skill.write_text("# Original\n", encoding="utf-8")
            _ = wrapper.write_text("# wrapper\n", encoding="utf-8")
            _ = runner.write_text("# runner\n", encoding="utf-8")
            _ = preregistration.write_text("{}\n", encoding="utf-8")
            for command in (
                ["git", "init", "-q", str(root)],
                ["git", "-C", str(root), "config", "user.email", "tests@example.invalid"],
                ["git", "-C", str(root), "config", "user.name", "V8 test"],
                ["git", "-C", str(root), "add", "."],
                ["git", "-C", str(root), "commit", "-qm", "freeze inputs"],
            ):
                _ = subprocess.run(command, check=True, capture_output=True)
            commit = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
            arguments = [
                "--corpus", str(corpus), "--prompts", str(prompts), "--skill", str(skill), "--codex", str(wrapper),
                "--preregistration", str(preregistration), "--preregistration-commit", commit,
                "--raw-output", str(root / "raw"), "--output", str(root / "result.json"),
            ]
            with patch.object(v8, "__file__", str(runner)):
                with v8.frozen_execution(arguments) as staged:
                    _ = skill.write_text("# Replaced after validation\n", encoding="utf-8")
                    staged_skill = Path(staged.arguments[staged.arguments.index("--skill") + 1])
                    self.assertEqual(staged_skill.read_text(encoding="utf-8"), "# Original\n")
                    self.assertEqual(staged.script_root, staged_skill.parent / "scripts")

    def test_v8_rejects_symbolic_links_stored_in_the_frozen_git_archive(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory)
            _ = (root / "regular.txt").write_text("tracked\n", encoding="utf-8")
            (root / "linked.txt").symlink_to("regular.txt")
            for command in (
                ["git", "init", "-q", str(root)],
                ["git", "-C", str(root), "config", "user.email", "tests@example.invalid"],
                ["git", "-C", str(root), "config", "user.name", "V8 test"],
                ["git", "-C", str(root), "add", "."],
                ["git", "-C", str(root), "commit", "-qm", "archive symlink"],
            ):
                _ = subprocess.run(command, check=True, capture_output=True)
            commit = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
            with self.assertRaisesRegex(ValueError, "only regular files and directories"):
                v8.validate_frozen_archive(root, commit)

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
