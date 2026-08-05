from pathlib import Path
from typing import TypedDict


ALLOWED_CHANGE: Path
HIDDEN_TEST: str


class SuiteReport(TypedDict):
    exit_code: int
    stdout: str
    stderr: str
    passed: bool


class CandidateReport(TypedDict):
    allowed_change: str
    changed_paths: list[str]
    only_canonical_owner_changed: bool
    public: SuiteReport
    hidden: SuiteReport
    passed: bool


def run_suite(candidate_root: Path, test_directory: Path, pattern: str) -> SuiteReport: ...
def score_candidate(candidate_root: Path) -> CandidateReport: ...
