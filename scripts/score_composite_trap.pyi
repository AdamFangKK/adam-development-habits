from collections.abc import Callable
from typing import TypedDict


class TrapResult(TypedDict):
    id: str
    passed: bool
    critical: bool
    description: str


class ScoreReport(TypedDict):
    score: int
    maximum_score: int
    threshold: int
    critical_misses: list[str]
    passed: bool
    results: list[TrapResult]


class Trap:
    identifier: str
    description: str
    critical: bool
    matches: Callable[[str], bool]


TRAPS: tuple[Trap, ...]


def score_response(response: str) -> ScoreReport: ...
