from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import cast


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from create_effect_preregistration_v9 import create  # noqa: E402


class EffectPreregistrationV9Tests(unittest.TestCase):
    def test_preregistration_captures_all_frozen_inputs_and_refuses_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            corpus = root / "corpus"
            corpus.mkdir()
            tasks = [
                {"task_id": f"task-{index}", "cohort": "decision-retention" if index < 20 else "repair", "stratum": "single-module"}
                for index in range(40)
            ]
            (corpus / "manifest.json").write_text(json.dumps({"tasks": tasks}), encoding="utf-8")
            prompts = root / "prompts"
            prompts.mkdir()
            for name in ("no_skill.txt", "old_skill.txt", "new_skill.txt"):
                (prompts / name).write_text(name, encoding="utf-8")
            files = {}
            for name in ("old", "new", "runner", "scorer", "analyzer", "auditor", "generator", "wrapper"):
                path = root / name
                path.write_text(name, encoding="utf-8")
                files[name.replace("runner", "runner").replace("scorer", "scorer").replace("analyzer", "analyzer").replace("auditor", "auditor").replace("generator", "generator").replace("wrapper", "wrapper")] = path
            output = root / "prereg.json"
            record = create(
                corpus=corpus, prompts=prompts, old_skill=files["old"], new_skill=files["new"],
                runner=files["runner"], scorer=files["scorer"], analyzer=files["analyzer"], auditor=files["auditor"],
                generator=files["generator"], wrapper=files["wrapper"], output=output, git_commit="a" * 40,
                model="model", harness="harness",
            )
            self.assertEqual(record["schema_version"], 2)
            task_plan = cast(dict[str, object], record["task_plan"])
            protocol = cast(dict[str, object], record["protocol"])
            self.assertEqual(len(cast(list[dict[str, object]], task_plan["tasks"])), 40)
            self.assertEqual(protocol["conditions"], ["no_skill", "old_skill", "new_skill"])
            self.assertEqual(protocol["codex_cli_version"], "codex-cli 0.149.0-alpha.4.1")
            self.assertEqual(protocol["codex_auth_mode"], "chatgpt")
            self.assertEqual(protocol["connectivity_probe_timeout_seconds"], 60.0)
            with self.assertRaises(FileExistsError):
                _ = create(
                    corpus=corpus, prompts=prompts, old_skill=files["old"], new_skill=files["new"],
                    runner=files["runner"], scorer=files["scorer"], analyzer=files["analyzer"], auditor=files["auditor"],
                    generator=files["generator"], wrapper=files["wrapper"], output=output, git_commit="a" * 40,
                    model="model", harness="harness",
                )

    def test_preregistration_accepts_api_key_mode_and_rejects_unknown_mode(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            corpus = root / "corpus"
            corpus.mkdir()
            tasks = [
                {"task_id": f"task-{index}", "cohort": "decision-retention" if index < 20 else "repair", "stratum": "single-module"}
                for index in range(40)
            ]
            (corpus / "manifest.json").write_text(json.dumps({"tasks": tasks}), encoding="utf-8")
            prompts = root / "prompts"
            prompts.mkdir()
            for name in ("no_skill.txt", "old_skill.txt", "new_skill.txt"):
                (prompts / name).write_text(name, encoding="utf-8")
            files = {}
            for name in ("old", "new", "runner", "scorer", "analyzer", "auditor", "generator", "wrapper"):
                path = root / name
                path.write_text(name, encoding="utf-8")
                files[name] = path
            record = create(
                corpus=corpus, prompts=prompts, old_skill=files["old"], new_skill=files["new"],
                runner=files["runner"], scorer=files["scorer"], analyzer=files["analyzer"], auditor=files["auditor"],
                generator=files["generator"], wrapper=files["wrapper"], output=root / "api-key.json", git_commit="b" * 40,
                model="model", harness="harness", auth_mode="api-key",
            )
            protocol = cast(dict[str, object], record["protocol"])
            self.assertEqual(protocol["codex_auth_mode"], "api-key")
            with self.assertRaisesRegex(ValueError, "unsupported Codex authentication mode"):
                _ = create(
                    corpus=corpus, prompts=prompts, old_skill=files["old"], new_skill=files["new"],
                    runner=files["runner"], scorer=files["scorer"], analyzer=files["analyzer"], auditor=files["auditor"],
                    generator=files["generator"], wrapper=files["wrapper"], output=root / "invalid.json", git_commit="c" * 40,
                    model="model", harness="harness", auth_mode="unsupported",
                )


if __name__ == "__main__":
    _ = unittest.main()
