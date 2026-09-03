from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SkillEntrypointLayoutTests(unittest.TestCase):
    def test_only_root_skill_file_is_discoverable(self) -> None:
        discovered = sorted(
            path.relative_to(ROOT).as_posix()
            for path in ROOT.rglob("SKILL.md")
            if ".git" not in path.parts
        )
        self.assertEqual(discovered, ["SKILL.md"])

    def test_experiment_snapshots_use_non_entrypoint_name(self) -> None:
        snapshots = sorted(
            path.relative_to(ROOT).as_posix()
            for path in ROOT.glob("examples/**/skills/*/frozen-policy.md")
        )
        self.assertGreaterEqual(len(snapshots), 16)
        self.assertTrue(all(path.endswith("/frozen-policy.md") for path in snapshots))


if __name__ == "__main__":
    _ = unittest.main()
