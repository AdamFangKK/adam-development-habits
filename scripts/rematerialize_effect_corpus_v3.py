#!/usr/bin/env python3
"""Create a second held-out split without changing the pinned QuixBugs source."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import cast


@dataclass(frozen=True)
class Arguments:
    source: Path
    output: Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json_lines(path: Path, rows: list[object]) -> None:
    _ = path.write_text("".join(json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def write_public_test(path: Path, function_name: str) -> None:
    _ = path.write_text(
        """import importlib.util
import json
import signal
from pathlib import Path

ROOT = Path(__file__).parent
spec = importlib.util.spec_from_file_location("buggy", ROOT / "buggy.py")
if spec is None or spec.loader is None:
    raise RuntimeError("cannot load buggy.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
cases = [json.loads(line) for line in (ROOT / "public_cases.json").read_text().splitlines() if line.strip()]

class CallTimeout(Exception):
    pass

def alarm_handler(signum, frame):
    raise CallTimeout("function call exceeded one second")

signal.signal(signal.SIGALRM, alarm_handler)
for input_data, expected in cases:
    signal.setitimer(signal.ITIMER_REAL, 1.0)
    try:
        actual = getattr(module, FUNCTION_NAME)(*input_data)
        if FUNCTION_NAME in {"flatten", "kheapsort"}:
            actual = list(actual)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
    if actual != expected:
        raise AssertionError(f"input={input_data!r}: expected={expected!r}, actual={actual!r}")
print(f"{len(cases)} public cases passed")
""".replace("FUNCTION_NAME", repr(function_name)),
        encoding="utf-8",
    )


def materialize(source_root: Path, output_root: Path) -> None:
    if output_root.exists():
        raise SystemExit(f"refusing to overwrite existing corpus: {output_root}")
    manifest = cast(dict[str, object], json.loads((source_root / "manifest.json").read_text(encoding="utf-8")))
    tasks = cast(list[object], manifest["tasks"])
    records: list[dict[str, object]] = []
    (output_root / "tasks").mkdir(parents=True)
    (output_root / "hidden").mkdir()
    _ = shutil.copy2(source_root / "QUIXBUGS-LICENSE", output_root / "QUIXBUGS-LICENSE")
    for raw_task in tasks:
        task = cast(dict[str, object], raw_task)
        task_id = cast(str, task["task_id"])
        source_task = source_root / "tasks" / task_id
        old_public = [json.loads(line) for line in (source_task / "public_cases.json").read_text(encoding="utf-8").splitlines() if line.strip()]
        old_hidden = [json.loads(line) for line in (source_root / cast(str, task["hidden_cases_path"])).read_text(encoding="utf-8").splitlines() if line.strip()]
        rows = old_public + old_hidden
        public_count = max(2, len(rows) // 3)
        public_rows = rows[:public_count]
        hidden_rows = rows[public_count:]
        target = output_root / "tasks" / task_id
        target.mkdir()
        for name in ("buggy.py", "task.md"):
            _ = shutil.copy2(source_task / name, target / name)
        write_json_lines(target / "public_cases.json", public_rows)
        write_public_test(target / "test_public.py", cast(str, task["function"]))
        hidden_path = output_root / "hidden" / f"{task_id}.json"
        write_json_lines(hidden_path, hidden_rows)
        records.append(
            {
                "task_id": task_id,
                "stratum": task["stratum"],
                "function": task["function"],
                "source_path": f"tasks/{task_id}/buggy.py",
                "public_cases_path": f"tasks/{task_id}/public_cases.json",
                "hidden_cases_path": f"hidden/{task_id}.json",
                "public_case_count": len(public_rows),
                "hidden_case_count": len(hidden_rows),
                "source_sha256": sha256(target / "buggy.py"),
                "public_cases_sha256": sha256(target / "public_cases.json"),
                "hidden_cases_sha256": sha256(hidden_path),
            }
        )
    output_manifest = {
        "schema_version": 1,
        "source": manifest["source"],
        "split": {"rule": "first max(2, floor(n/3)) public; remainder hidden from the v1 ordered cases", "hidden_reference_available_only_to_scorer": True},
        "tasks": records,
    }
    _ = (output_root / "manifest.json").write_text(json.dumps(output_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    _ = parser.add_argument("--source", type=Path, required=True)
    _ = parser.add_argument("--output", type=Path, required=True)
    parsed = parser.parse_args()
    args = Arguments(source=cast(Path, parsed.source), output=cast(Path, parsed.output))
    materialize(args.source, args.output)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
