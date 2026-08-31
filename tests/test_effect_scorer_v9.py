from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from score_effect_workspace_v9 import score_workspace  # noqa: E402


COMMAND = [sys.executable, "-m", "unittest", "discover", "-s", "tests"]


class EffectScorerV9Tests(unittest.TestCase):
    def make_workspace(self, root: Path, value: int) -> Path:
        workspace = root / "workspace"
        tests = workspace / "tests"
        tests.mkdir(parents=True)
        _ = (workspace / "owner.py").write_text(f"value = {value}\n", encoding="utf-8")
        _ = (tests / "test_public.py").write_text(
            "import unittest\nimport owner\n\n"
            "class Public(unittest.TestCase):\n"
            "    def test_public(self):\n"
            "        self.assertGreaterEqual(owner.value, 0)\n",
            encoding="utf-8",
        )
        return workspace

    def make_hidden(self, root: Path, expected: int = 42) -> Path:
        hidden = root / "hidden-tests"
        tests = hidden / "tests"
        tests.mkdir(parents=True)
        _ = (tests / "test_hidden.py").write_text(
            "import unittest\nimport owner\n\n"
            "class Hidden(unittest.TestCase):\n"
            "    def test_hidden(self):\n"
            f"        self.assertEqual(owner.value, {expected})\n",
            encoding="utf-8",
        )
        return hidden

    def test_buggy_candidate_cannot_be_overwritten_by_a_reference(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = self.make_workspace(root, 1)
            hidden = self.make_hidden(root)
            reference = root / "reference"
            reference.mkdir()
            _ = (reference / "owner.py").write_text("value = 42\n", encoding="utf-8")

            report = score_workspace(workspace, hidden, ("owner.py",), COMMAND, timeout=5)

            self.assertFalse(report["passed"], report)
            self.assertTrue(report["implementation_integrity_passed"], report)
            self.assertEqual((workspace / "owner.py").read_text(encoding="utf-8"), "value = 1\n")

    def test_fixed_candidate_passes_and_retains_implementation_hash(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = self.make_workspace(root, 42)
            hidden = self.make_hidden(root)

            report = score_workspace(workspace, hidden, ("owner.py",), COMMAND, timeout=5)

            self.assertTrue(report["passed"], report)
            self.assertTrue(report["implementation_integrity_passed"], report)
            self.assertEqual(report["injected_hidden_tests"], ["tests/test_hidden.py"])

    def test_hidden_root_rejects_source_files_and_collisions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = self.make_workspace(root, 42)
            hidden = self.make_hidden(root)
            _ = (hidden / "owner.py").write_text("value = 42\n", encoding="utf-8")
            report = score_workspace(workspace, hidden, ("owner.py",), COMMAND, timeout=5)
            self.assertFalse(report["passed"], report)
            self.assertIn("only the tests directory", str(report["stderr"]))

            _ = (hidden / "owner.py").unlink()
            _ = (hidden / "tests" / "test_hidden.py").replace(hidden / "tests" / "test_public.py")
            collision = score_workspace(workspace, hidden, ("owner.py",), COMMAND, timeout=5)
            self.assertFalse(collision["passed"], collision)
            self.assertIn("collides", str(collision["stderr"]))


if __name__ == "__main__":
    _ = unittest.main()
