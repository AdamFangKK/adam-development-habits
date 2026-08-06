#!/usr/bin/env python3
"""Check that an unrun Causal Full counterfactual ends in calibrated uncertainty."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import TypedDict


class CalibrationReport(TypedDict):
    passed: bool
    counterfactual_unrun: bool
    conclusion: str | None
    issues: list[str]


class Arguments(argparse.Namespace):
    output: Path = Path()
    require_unknown: bool = False


UNRUN_COUNTERFACTUAL = re.compile(
    r"(?:"
    + r"counterfactual(?:\s+actual)?\s+result\s*:\s*(?:unrun|not run|unavailable|read-only|proposed(?:\s+only)?|in-memory(?:\s+only)?)"
    + r"|counterfactual\s+(?:was\s+)?(?:only\s+)?proposed"
    + r"|execution\s+authority\s*:\s*read-only"
    + r"|counterfactual\s+status\s*:\s*(?:unrun|in-memory(?:-only)?|proposed|blocked)"
    + r"|in-memory\s+(?:probe|counterfactual)"
    + r")",
    re.IGNORECASE,
)
READ_ONLY_AUTHORITY = re.compile(r"execution\s+authority\s*:\s*read-only", re.IGNORECASE)
EXECUTED_INTERVENTION = re.compile(
    r"execution\s+authority\s*:\s*authorized\s+code-changing\s+worktree.*"
    + r"counterfactual\s+status\s*:\s*executed.*"
    + r"candidate\s+diff.*"
    + r"before/after\s+(?:command|test)\s+output",
    re.IGNORECASE | re.DOTALL,
)
CONCLUSION_LINE = re.compile(r"^Causal conclusion:\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE)


def score_output(output: str, *, require_unknown: bool = False) -> CalibrationReport:
    """Return whether a transcript calibrates an unrun intervention as unknown."""
    raw_unrun = UNRUN_COUNTERFACTUAL.search(output) is not None
    executed = EXECUTED_INTERVENTION.search(output) is not None
    unrun = READ_ONLY_AUTHORITY.search(output) is not None or (raw_unrun and not executed)
    conclusion_match = CONCLUSION_LINE.search(output)
    conclusion = conclusion_match.group(1).strip().strip("*") if conclusion_match else None
    issues: list[str] = []
    if conclusion not in {"root-cause fix", "mitigation", "instrumentation-only", "unknown"}:
        issues.append("a Causal Full transcript requires one exact Causal conclusion terminal label")
    if require_unknown and conclusion != "unknown":
        issues.append("this read-only evaluation requires the exact line 'Causal conclusion: unknown'")
    if unrun and conclusion != "unknown":
        issues.append("an unrun counterfactual requires the exact line 'Causal conclusion: unknown'")
    return {
        "passed": not issues,
        "counterfactual_unrun": unrun,
        "conclusion": conclusion,
        "issues": issues,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Score causal-calibration output.")
    _ = parser.add_argument("output", type=Path, help="Markdown transcript to score")
    _ = parser.add_argument("--require-unknown", action="store_true", help="Require the read-only unknown conclusion")
    arguments = parser.parse_args(namespace=Arguments())
    report = score_output(arguments.output.read_text(encoding="utf-8"), require_unknown=arguments.require_unknown)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
