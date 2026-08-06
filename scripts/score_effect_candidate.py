#!/usr/bin/env python3
"""Blindly score one repair candidate against held-out QuixBugs cases."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import TypedDict, cast


class CandidateReport(TypedDict):
    task_id: str
    candidate_sha256: str
    passed: bool
    passed_cases: int
    total_cases: int
    failures: list[dict[str, object]]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def helper_source(candidate: Path, function_name: str, cases: list[list[object]]) -> str:
    encoded_cases = json.dumps(cases, ensure_ascii=True, separators=(",", ":"))
    return f"""
import importlib.util
import json
import signal
import sys

candidate = {str(candidate)!r}
function_name = {function_name!r}
cases = json.loads({encoded_cases!r})
sys.path.insert(0, str(__import__('pathlib').Path(candidate).parent))
spec = importlib.util.spec_from_file_location('candidate_module', candidate)
if spec is None or spec.loader is None:
    raise RuntimeError('cannot load candidate')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class CallTimeout(Exception):
    pass

def alarm_handler(signum, frame):
    raise CallTimeout('function call exceeded one second')

signal.signal(signal.SIGALRM, alarm_handler)
for index, input_data in enumerate(cases):
    signal.setitimer(signal.ITIMER_REAL, 1.0)
    try:
        value = getattr(module, function_name)(*input_data)
        if function_name in {{'flatten', 'kheapsort'}}:
            value = list(value)
        rendered = json.dumps(value, ensure_ascii=True, sort_keys=True)
        print(json.dumps({{'index': index, 'status': 'ok', 'value': rendered}}, ensure_ascii=True), flush=True)
    except Exception as error:
        print(json.dumps({{'index': index, 'status': 'error', 'error': f'{{type(error).__name__}}: {{error}}'}}, ensure_ascii=True), flush=True)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
"""


def score_candidate(candidate: Path, hidden_cases: Path, *, task_id: str, function_name: str, timeout: float) -> CandidateReport:
    rows = [json.loads(line) for line in hidden_cases.read_text(encoding="utf-8").splitlines() if line.strip()]
    cases = [cast(list[object], row[0]) for row in rows]
    expected = [row[1] for row in rows]
    environment = {
        "PATH": os.environ.get("PATH", ""),
        "PYTHONNOUSERSITE": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    failures: list[dict[str, object]] = []
    actual_by_index: dict[int, dict[str, object]] = {}
    try:
        with tempfile.TemporaryDirectory(prefix="adam-effect-score-") as directory:
            result = subprocess.run(
                [sys.executable, "-I", "-c", helper_source(candidate.resolve(), function_name, cases)],
                cwd=directory,
                env=environment,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        if result.returncode != 0 and not result.stdout:
            failures.append({"kind": "process", "detail": result.stderr.strip() or f"exit {result.returncode}"})
        for line in result.stdout.splitlines():
            try:
                record = cast(dict[str, object], json.loads(line))
                actual_by_index[int(record["index"])] = record
            except (ValueError, TypeError, json.JSONDecodeError) as error:
                failures.append({"kind": "protocol", "detail": str(error), "line": line})
    except subprocess.TimeoutExpired:
        failures.append({"kind": "process-timeout", "detail": f"scorer exceeded {timeout:.1f}s"})

    passed_cases = 0
    for index, (input_data, expected_value) in enumerate(zip(cases, expected)):
        record = actual_by_index.get(index)
        if record is None or record.get("status") != "ok":
            failures.append({"kind": "case", "index": index, "input": input_data, "detail": record or "no result"})
            continue
        try:
            actual_value = json.loads(cast(str, record["value"]))
        except (TypeError, json.JSONDecodeError) as error:
            failures.append({"kind": "case", "index": index, "input": input_data, "detail": f"invalid value: {error}"})
            continue
        if actual_value == expected_value:
            passed_cases += 1
        else:
            failures.append({"kind": "case", "index": index, "input": input_data, "expected": expected_value, "actual": actual_value})
    return {
        "task_id": task_id,
        "candidate_sha256": sha256(candidate),
        "passed": not failures and passed_cases == len(rows),
        "passed_cases": passed_cases,
        "total_cases": len(rows),
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    _ = parser.add_argument("--candidate", type=Path, required=True)
    _ = parser.add_argument("--hidden-cases", type=Path, required=True)
    _ = parser.add_argument("--task-id", required=True)
    _ = parser.add_argument("--function", required=True)
    _ = parser.add_argument("--timeout", type=float, default=10.0)
    arguments = parser.parse_args()
    report = score_candidate(
        arguments.candidate,
        arguments.hidden_cases,
        task_id=arguments.task_id,
        function_name=arguments.function,
        timeout=arguments.timeout,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
