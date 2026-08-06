from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from typing import Callable, ClassVar, Protocol, cast


ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "scripts" / "materialize_effect_corpus_v5.py"


class CorpusGenerator(Protocol):
    def materialize(self, output: Path) -> None: ...
    def reference(self, name: str) -> Callable[..., object]: ...


def load_generator() -> CorpusGenerator:
    spec = importlib.util.spec_from_file_location("effect_corpus_v5", GENERATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load corpus generator")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return cast(CorpusGenerator, cast(object, module))


class EffectCorpusV5Tests(unittest.TestCase):
    generator: ClassVar[CorpusGenerator]

    @classmethod
    def setUpClass(cls) -> None:  # pyright: ignore[reportImplicitOverride]
        cls.generator = load_generator()

    def test_generated_corpus_has_a_visible_bug_and_consistent_hidden_contract(self) -> None:
        with tempfile.TemporaryDirectory(prefix="effect-corpus-v5-") as directory:
            corpus = Path(directory) / "corpus"
            self.generator.materialize(corpus)
            manifest = cast(dict[str, object], json.loads((corpus / "manifest.json").read_text(encoding="utf-8")))
            tasks = cast(list[dict[str, object]], manifest["tasks"])
            self.assertEqual(22, len(tasks))
            self.assertEqual(Counter({"single-module": 10, "cross-module": 8, "integration": 4}), Counter(cast(str, task["stratum"]) for task in tasks))

            for task in tasks:
                with self.subTest(task=task["task_id"]):
                    public_path = corpus / cast(str, task["public_cases_path"])
                    hidden_path = corpus / cast(str, task["hidden_cases_path"])
                    self.assertEqual(hashlib.sha256(public_path.read_bytes()).hexdigest(), task["public_cases_sha256"])
                    self.assertEqual(hashlib.sha256(hidden_path.read_bytes()).hexdigest(), task["hidden_cases_sha256"])

                    public = [json.loads(line) for line in public_path.read_text(encoding="utf-8").splitlines() if line]
                    hidden = [json.loads(line) for line in hidden_path.read_text(encoding="utf-8").splitlines() if line]
                    self.assertTrue(public)
                    self.assertTrue(hidden)
                    reference = self.generator.reference(cast(str, task["function"]))
                    for row in cast(list[object], public + hidden):
                        self.assertIsInstance(row, list)
                        inputs, expected = cast(list[object], row)
                        self.assertIsInstance(inputs, list)
                        self.assertEqual(expected, reference(*cast(list[object], inputs)))

                    result = subprocess.run(
                        [sys.executable, "test_public.py"],
                        cwd=corpus / "tasks" / cast(str, task["task_id"]),
                        capture_output=True,
                        text=True,
                        timeout=5,
                        check=False,
                    )
                    self.assertNotEqual(0, result.returncode, "fixture must require a repair")


if __name__ == "__main__":
    _ = unittest.main()
