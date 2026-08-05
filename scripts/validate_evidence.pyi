from pathlib import Path
from typing import Any


def validate_evidence(
    data: Any,
    *,
    expected_change_id: str | None = ...,
    artifact_root: Path | None = ...,
) -> list[str]: ...
