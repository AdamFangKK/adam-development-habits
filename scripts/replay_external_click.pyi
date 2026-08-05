from pathlib import Path
from typing import TypedDict


BUGGY_REVISION: str
PATCH_REVISION: str
EXPECTED_TREES: dict[str, str]
EXPECTED_TYPES: dict[str, str]
CHECK_TIMEOUT_SECONDS: int


class CheckResult(TypedDict):
    exit_code: int
    passed: bool
    summary: str


class VariantResult(TypedDict):
    source_tree_sha256: str
    types_sha256: str
    public: CheckResult
    hidden: CheckResult
    passed: bool


class ReplayReport(TypedDict):
    schema_version: int
    source: dict[str, str]
    protocol: dict[str, str | bool]
    tool: dict[str, str]
    variants: dict[str, VariantResult]
    conclusion: dict[str, str | bool]


def replace_once(source: str, old: str, new: str, description: str) -> str: ...
def require_symlink_support() -> None: ...
def source_root(root: Path, label: str) -> Path: ...
def test_environment(root: Path, program: str, timeout_seconds: float = ...) -> CheckResult: ...
def replay(bug_root: Path, patch_root: Path) -> ReplayReport: ...
