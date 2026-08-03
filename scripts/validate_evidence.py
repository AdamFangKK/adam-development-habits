#!/usr/bin/env python3
"""Validate Adam's Development Habits evidence artifacts without dependencies."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


SAFEGUARD_STATUSES = {"applied", "not_applicable"}
VERIFICATION_STATUSES = {"passed", "not_applicable"}
REVIEW_OUTCOMES = {"approved"}


def is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def require_string(data: dict[str, Any], field: str, errors: list[str]) -> None:
    if not is_nonempty_string(data.get(field)):
        errors.append(f"{field} must be a non-empty string")


def require_string_list(data: dict[str, Any], field: str, errors: list[str], *, allow_empty: bool = False) -> None:
    value = data.get(field)
    if not isinstance(value, list) or (not allow_empty and not value):
        errors.append(f"{field} must be a {'possibly empty ' if allow_empty else 'non-empty '}list")
        return
    if any(not is_nonempty_string(item) for item in value):
        errors.append(f"{field} must contain only non-empty strings")


def validate_evidence(data: Any, *, expected_change_id: str | None = None) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["root value must be an object"]

    if data.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    require_string(data, "change_id", errors)
    if expected_change_id is not None and data.get("change_id") != expected_change_id:
        errors.append("change_id must match the evidence artifact filename")

    level = data.get("level")
    if level not in {1, 2}:
        errors.append("level must be 1 or 2")

    require_string_list(data, "canonical_owner", errors)
    require_string_list(data, "affected_callers", errors, allow_empty=True)
    require_string_list(data, "invariants", errors)
    require_string_list(data, "replaced_paths", errors, allow_empty=True)
    require_string_list(data, "remaining_risks", errors, allow_empty=True)

    criteria = data.get("acceptance_criteria")
    if not isinstance(criteria, list) or not criteria:
        errors.append("acceptance_criteria must be a non-empty list")
    else:
        for index, criterion in enumerate(criteria):
            if not isinstance(criterion, dict):
                errors.append(f"acceptance_criteria[{index}] must be an object")
                continue
            for field in ("id", "condition", "verification"):
                if not is_nonempty_string(criterion.get(field)):
                    errors.append(f"acceptance_criteria[{index}].{field} must be a non-empty string")

    compatibility = data.get("retained_compatibility")
    if not isinstance(compatibility, list):
        errors.append("retained_compatibility must be a list")
    else:
        for index, item in enumerate(compatibility):
            if not isinstance(item, dict):
                errors.append(f"retained_compatibility[{index}] must be an object")
                continue
            for field in ("consumer", "removal_condition", "test"):
                if not is_nonempty_string(item.get(field)):
                    errors.append(f"retained_compatibility[{index}].{field} must be a non-empty string")

    safeguards = data.get("safeguards")
    if not isinstance(safeguards, list) or not safeguards:
        errors.append("safeguards must be a non-empty list")
    else:
        for index, safeguard in enumerate(safeguards):
            if not isinstance(safeguard, dict):
                errors.append(f"safeguards[{index}] must be an object")
                continue
            require_string(safeguard, "name", errors)
            if safeguard.get("status") not in SAFEGUARD_STATUSES:
                errors.append(f"safeguards[{index}].status must be applied or not_applicable")
            require_string(safeguard, "rationale", errors)

    verification = data.get("verification")
    if not isinstance(verification, list) or not verification:
        errors.append("verification must be a non-empty list")
    else:
        for index, item in enumerate(verification):
            if not isinstance(item, dict):
                errors.append(f"verification[{index}] must be an object")
                continue
            require_string(item, "command", errors)
            if item.get("status") not in VERIFICATION_STATUSES:
                errors.append(f"verification[{index}].status must be passed or not_applicable")
            require_string(item, "result", errors)
        if not any(item.get("status") == "passed" for item in verification if isinstance(item, dict)):
            errors.append("verification must contain at least one passed result")

    if level == 2:
        require_string(data, "rollback_or_compatibility", errors)
        review = data.get("independent_review")
        if not isinstance(review, dict):
            errors.append("independent_review must be an object for level 2")
        else:
            require_string(review, "reviewer", errors)
            if review.get("outcome") not in REVIEW_OUTCOMES:
                errors.append("independent_review.outcome must be approved")
            require_string(review, "notes", errors)

    return errors


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as source:
        return json.load(source)


def is_evidence_artifact(path: Path) -> bool:
    return path.parent.name == "evidence" and path.parent.parent.name == ".adam"


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Adam's Development Habits evidence artifacts.")
    parser.add_argument("artifacts", nargs="+", type=Path, help="JSON evidence artifact paths")
    args = parser.parse_args()

    failed = False
    for artifact in args.artifacts:
        try:
            expected_change_id = artifact.stem if is_evidence_artifact(artifact) else None
            errors = validate_evidence(load_json(artifact), expected_change_id=expected_change_id)
        except (OSError, json.JSONDecodeError) as error:
            errors = [str(error)]
        if errors:
            failed = True
            for error in errors:
                print(f"{artifact}: {error}", file=sys.stderr)
        else:
            print(f"valid evidence: {artifact}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
