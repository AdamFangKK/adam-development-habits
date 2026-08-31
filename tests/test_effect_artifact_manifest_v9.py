from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import cast


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from generate_effect_artifact_manifest_v9 import generate  # noqa: E402


class EffectArtifactManifestV9Tests(unittest.TestCase):
    def test_manifest_hashes_all_required_files_and_refuses_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = root / "raw"
            artifact = raw / "task-1" / "no_skill"
            artifact.mkdir(parents=True)
            for filename in ("agent.stdout.log", "agent.stderr.log", "agent-output.md", "candidate.diff", "public.json", "hidden-score.json"):
                (artifact / filename).write_text(filename + "\n", encoding="utf-8")
            result = root / "result.json"
            result.write_text(json.dumps({"trials": [{
                "task_id": "task-1", "condition": "no_skill", "cohort": "repair", "stratum": "integration",
                "execution_order": 1, "replicate_index": 1, "artifact_path": "task-1/no_skill",
                "trial_complete": True, "hidden_repair_pass": False, "implementation_integrity_passed": True,
            }]}), encoding="utf-8")
            output = root / "manifest.json"
            manifest = generate(raw, result, output)
            self.assertEqual(manifest["trial_count"], 1)
            entries = cast(list[dict[str, object]], manifest["entries"])
            self.assertEqual(len(cast(list[dict[str, object]], entries[0]["files"])), 6)
            with self.assertRaises(FileExistsError):
                _ = generate(raw, result, output)


if __name__ == "__main__":
    _ = unittest.main()
