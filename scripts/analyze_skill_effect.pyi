from collections.abc import Mapping
from pathlib import Path
from typing import TypedDict


class MetricReport(TypedDict):
    metric: str
    eligible: bool
    decision: str
    distinct_tasks: int
    paired_runs: int
    effect: float | None
    confidence_interval_95: list[float] | None
    one_sided_randomization_p_value: float | None
    randomization_method: str | None
    reason: str | None


class AnalysisReport(TypedDict):
    experiment_id: str
    status: str
    scope: dict[str, object]
    primary_metric: MetricReport
    secondary_metric: MetricReport
    conclusion: str
    limitations: list[str]


class ExperimentError(ValueError): ...


def canonical_sha256(value: object) -> str: ...
def immutable_envelope(experiment: Mapping[str, object]) -> dict[str, object]: ...
def skill_first_for(random_seed: int, task_id: str, replicate_index: int) -> bool: ...
def load_experiment(path: Path) -> dict[str, object]: ...
def analyze_experiment(experiment: Mapping[str, object]) -> AnalysisReport: ...
