#!/usr/bin/env python3
"""Materialize a pinned, split QuixBugs repair corpus for paired evaluation."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import TypedDict


TASK_STRATA = {
    "single-module": (
        "bitcount",
        "gcd",
        "is_valid_parenthesization",
        "lcs_length",
        "lis",
        "max_sublist_sum",
        "next_palindrome",
        "possible_change",
    ),
    "cross-module": (
        "bucketsort",
        "find_first_in_sorted",
        "find_in_sorted",
        "flatten",
        "get_factors",
        "hanoi",
        "kth",
        "longest_common_subsequence",
    ),
    "integration": (
        "kheapsort",
        "knapsack",
        "levenshtein",
        "mergesort",
    ),
}


class TaskRecord(TypedDict):
    task_id: str
    stratum: str
    function: str
    source_path: str
    public_cases_path: str
    hidden_cases_path: str
    public_case_count: int
    hidden_case_count: int
    source_sha256: str
    public_cases_sha256: str
    hidden_cases_sha256: str


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json_lines(destination: Path, rows: list[object]) -> None:
    destination.write_text(
        "".join(json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def write_public_test(destination: Path, function_name: str) -> None:
    destination.write_text(
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


def normalize(value):
    return list(value) if FUNCTION_NAME in {"flatten", "kheapsort"} else value


class CallTimeout(Exception):
    pass


def alarm_handler(signum, frame):
    raise CallTimeout("function call exceeded one second")


signal.signal(signal.SIGALRM, alarm_handler)


for input_data, expected in cases:
    signal.setitimer(signal.ITIMER_REAL, 1.0)
    try:
        actual = normalize(getattr(module, FUNCTION_NAME)(*input_data))
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
    if actual != expected:
        raise AssertionError(f"input={input_data!r}: expected={expected!r}, actual={actual!r}")

print(f"{len(cases)} public cases passed")
""".replace("FUNCTION_NAME", repr(function_name)),
        encoding="utf-8",
    )


def materialize(quixbugs_root: Path, output_root: Path, source_commit: str) -> None:
    if not (quixbugs_root / "python_programs").is_dir():
        raise SystemExit(f"not a QuixBugs checkout: {quixbugs_root}")
    if output_root.exists():
        raise SystemExit(f"refusing to overwrite existing corpus: {output_root}")

    tasks_root = output_root / "tasks"
    data_root = output_root / "hidden"
    tasks_root.mkdir(parents=True)
    data_root.mkdir()
    records: list[TaskRecord] = []
    for stratum, task_ids in TASK_STRATA.items():
        for task_id in task_ids:
            source = quixbugs_root / "python_programs" / f"{task_id}.py"
            cases = quixbugs_root / "json_testcases" / f"{task_id}.json"
            if not source.is_file() or not cases.is_file():
                raise SystemExit(f"missing QuixBugs input for {task_id}")
            rows = [json.loads(line) for line in cases.read_text(encoding="utf-8").splitlines() if line.strip()]
            if len(rows) < 3:
                raise SystemExit(f"{task_id} needs at least three cases")
            public_count = max(1, (len(rows) * 3) // 5)
            public_rows = rows[:public_count]
            hidden_rows = rows[public_count:]
            task_root = tasks_root / task_id
            task_root.mkdir()
            shutil.copy2(source, task_root / "buggy.py")
            (task_root / "task.md").write_text(
                f"Repair the implementation of `{task_id}` in `buggy.py`. "
                "Preserve the public function contract, do not edit `public_cases.json`, "
                "and keep the change limited to the implementation. Run the supplied public test command before finishing.\n",
                encoding="utf-8",
            )
            write_json_lines(task_root / "public_cases.json", public_rows)
            write_public_test(task_root / "test_public.py", task_id)
            hidden_path = data_root / f"{task_id}.json"
            write_json_lines(hidden_path, hidden_rows)
            record: TaskRecord = {
                "task_id": task_id,
                "stratum": stratum,
                "function": task_id,
                "source_path": f"tasks/{task_id}/buggy.py",
                "public_cases_path": f"tasks/{task_id}/public_cases.json",
                "hidden_cases_path": f"hidden/{task_id}.json",
                "public_case_count": len(public_rows),
                "hidden_case_count": len(hidden_rows),
                "source_sha256": sha256(task_root / "buggy.py"),
                "public_cases_sha256": sha256(task_root / "public_cases.json"),
                "hidden_cases_sha256": sha256(hidden_path),
            }
            records.append(record)
    shutil.copy2(quixbugs_root / "LICENSE", output_root / "QUIXBUGS-LICENSE")
    manifest = {
        "schema_version": 1,
        "source": {
            "name": "QuixBugs",
            "repository": "https://github.com/jkoppel/QuixBugs",
            "commit": source_commit,
            "license_path": "QUIXBUGS-LICENSE",
        },
        "split": {
            "rule": "ordered JSON cases; first floor(3/5) public, remainder hidden",
            "hidden_reference_available_only_to_scorer": True,
        },
        "tasks": records,
    }
    (output_root / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    _ = parser.add_argument("--quixbugs-root", type=Path, required=True)
    _ = parser.add_argument("--output", type=Path, required=True)
    _ = parser.add_argument("--source-commit", required=True)
    arguments = parser.parse_args()
    materialize(arguments.quixbugs_root, arguments.output, arguments.source_commit)
    print(json.dumps({"output": str(arguments.output), "manifest": str(arguments.output / "manifest.json")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
