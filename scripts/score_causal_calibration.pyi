from typing import TypedDict


class CalibrationReport(TypedDict):
    passed: bool
    counterfactual_unrun: bool
    conclusion: str | None
    issues: list[str]


def score_output(output: str, *, require_unknown: bool = False) -> CalibrationReport: ...
