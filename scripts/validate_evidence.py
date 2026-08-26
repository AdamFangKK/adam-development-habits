#!/usr/bin/env python3
"""Validate Adam's Development Habits evidence artifacts without dependencies."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, cast


SAFEGUARD_STATUSES = {"applied", "not_applicable"}
VERIFICATION_STATUSES = {"passed", "not_applicable"}
REVIEW_OUTCOMES = {"approved"}
NON_INDEPENDENT_REVIEWERS = {
    "author",
    "automated contract tests",
    "code author",
    "executor",
    "implementation agent",
    "implementer",
    "same agent",
    "self",
    "self review",
}
SUPPORTED_SCHEMA_VERSIONS = {1, 2}
CAUSAL_MODES = {"lite", "full"}
CAUSAL_HYPOTHESIS_STATUSES = {"supported", "rejected", "unresolved"}
CAUSAL_EVIDENCE_TYPES = {"observational", "reproduction", "intervention"}
CAUSAL_CONCLUSIONS = {"root_cause_fix", "mitigation", "instrumentation_only", "unknown"}
CAUSAL_CONFIDENCE = {"low", "medium", "high"}
CAUSAL_ARTIFACT_KINDS = {"command_output", "diff", "test_output", "test_source", "trace_export"}
CAUSAL_EXECUTION_ARTIFACT_KINDS = {"command_output", "test_output", "trace_export"}
QUALITY_DECISION_FIELDS = (
    "design_boundary",
    "dependency_audit",
    "extension_decision",
    "data_ownership",
    "error_model",
    "contract_evolution",
    "operational_budget",
    "threat_boundary",
    "delivery_lifecycle",
    "release_recovery",
    "data_migration",
    "configuration_secrets",
    "dependency_supply_chain",
    "operational_knowledge",
    "reproducibility",
)
SUPPORTING_ARTIFACT_KINDS = {"command_output", "diff", "evaluation_transcript", "review_report", "test_output"}
VERIFICATION_ARTIFACT_KINDS = {"command_output", "test_output"}


def is_nonempty_string(value: object) -> bool:
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


def is_sha256(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def is_execution_timestamp(value: object) -> bool:
    if not isinstance(value, str) or "T" not in value or not value.endswith("Z"):
        return False
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return False
    return parsed.utcoffset() == timedelta(0)


def is_repository_revision(value: object) -> bool:
    if not isinstance(value, str):
        return False
    commit = value.removesuffix("+worktree")
    return commit != "0" * 40 and len(commit) == 40 and all(character in "0123456789abcdef" for character in commit)


def repository_revision_exists(value: str, artifact_root: Path) -> bool:
    commit = value.removesuffix("+worktree")
    result = subprocess.run(
        ["git", "-C", str(artifact_root.resolve()), "cat-file", "-e", f"{commit}^{{commit}}"],
        check=False,
        capture_output=True,
    )
    return result.returncode == 0


def normalized_reviewer(value: str) -> str:
    return " ".join(value.casefold().replace("-", " ").replace("_", " ").split())


def read_artifact_bytes(
    artifact: dict[str, Any],
    artifact_root: Path,
    errors: list[str],
    label: str,
) -> bytes | None:
    path_value = artifact.get("path")
    if not is_nonempty_string(path_value):
        return None

    path = Path(cast(str, path_value))
    if path.is_absolute() or ".." in path.parts:
        errors.append(f"{label}.path must stay inside the artifact root")
        return None

    root = artifact_root.resolve()
    resolved = (root / path).resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        errors.append(f"{label}.path must stay inside the artifact root")
        return None

    git_commit = artifact.get("git_commit")
    if git_commit is not None:
        if not isinstance(git_commit, str) or len(git_commit) != 40 or not all(
            character in "0123456789abcdef" for character in git_commit
        ):
            errors.append(f"{label}.git_commit must be a full lowercase Git commit SHA")
            return None
        commit_check = subprocess.run(
            ["git", "-C", str(root), "cat-file", "-e", f"{git_commit}^{{commit}}"],
            check=False,
            capture_output=True,
        )
        if commit_check.returncode != 0:
            errors.append(f"{label}.git_commit does not reference a commit in the artifact repository")
            return None
        blob = subprocess.run(
            ["git", "-C", str(root), "show", f"{git_commit}:{path.as_posix()}"],
            check=False,
            capture_output=True,
        )
        if blob.returncode != 0:
            errors.append(f"{label}.path does not reference a file at git_commit")
            return None
        return blob.stdout

    if not resolved.is_file():
        errors.append(f"{label}.path does not reference a file")
        return None
    return resolved.read_bytes()


def validate_causal_artifact_path(artifact: dict[str, Any], artifact_root: Path, errors: list[str], index: int) -> None:
    content = read_artifact_bytes(artifact, artifact_root, errors, f"causal.evidence_artifacts[{index}]")
    if content is None:
        return
    digest = hashlib.sha256(content).hexdigest()
    if digest != artifact.get("sha256"):
        errors.append(f"causal.evidence_artifacts[{index}].sha256 does not match the referenced file")


def validate_supporting_artifact_path(artifact: dict[str, Any], artifact_root: Path, errors: list[str], index: int) -> None:
    content = read_artifact_bytes(artifact, artifact_root, errors, f"supporting_artifacts[{index}]")
    if content is None:
        return
    digest = hashlib.sha256(content).hexdigest()
    if digest != artifact.get("sha256"):
        errors.append(f"supporting_artifacts[{index}].sha256 does not match the referenced file")


def validate_quality_decisions(quality_decisions: Any, errors: list[str]) -> None:
    if not isinstance(quality_decisions, dict):
        errors.append("quality_decisions must be an object")
        return

    unknown_fields = set(quality_decisions).difference(QUALITY_DECISION_FIELDS)
    if unknown_fields:
        errors.append("quality_decisions contains unknown fields")

    for field in QUALITY_DECISION_FIELDS:
        decision = quality_decisions.get(field)
        if not isinstance(decision, dict):
            errors.append(f"quality_decisions.{field} must be an object")
            continue
        if decision.get("status") not in SAFEGUARD_STATUSES:
            errors.append(f"quality_decisions.{field}.status must be applied or not_applicable")
        require_string(decision, "rationale", errors)


def validate_supporting_artifacts(
    supporting_artifacts: Any,
    errors: list[str],
    *,
    artifact_root: Path | None = None,
    require_execution_metadata: bool = False,
) -> None:
    if not isinstance(supporting_artifacts, list) or not supporting_artifacts:
        errors.append("supporting_artifacts must be a non-empty list")
        return

    artifact_ids: set[str] = set()
    for index, artifact in enumerate(supporting_artifacts):
        if not isinstance(artifact, dict):
            errors.append(f"supporting_artifacts[{index}] must be an object")
            continue
        artifact_id = artifact.get("id")
        if not is_nonempty_string(artifact_id):
            errors.append(f"supporting_artifacts[{index}].id must be a non-empty string")
        elif artifact_id in artifact_ids:
            errors.append(f"supporting_artifacts[{index}].id must be unique")
        else:
            artifact_ids.add(cast(str, artifact_id))
        kind = artifact.get("kind")
        if kind not in SUPPORTING_ARTIFACT_KINDS:
            errors.append(
                f"supporting_artifacts[{index}].kind must be command_output, diff, evaluation_transcript, review_report, or test_output"
            )
        require_string(artifact, "path", errors)
        if not is_sha256(artifact.get("sha256")):
            errors.append(f"supporting_artifacts[{index}].sha256 must be a lowercase SHA-256 digest")
        require_string(artifact, "summary", errors)
        if require_execution_metadata and kind in VERIFICATION_ARTIFACT_KINDS:
            require_string(artifact, "command", errors)
            exit_code = artifact.get("exit_code")
            if not isinstance(exit_code, int) or isinstance(exit_code, bool):
                errors.append(f"supporting_artifacts[{index}].exit_code must be an integer")
            if not is_execution_timestamp(artifact.get("executed_at")):
                errors.append(f"supporting_artifacts[{index}].executed_at must be an RFC 3339 UTC timestamp")
            repository_revision = artifact.get("repository_revision")
            if not is_repository_revision(repository_revision):
                errors.append(
                    f"supporting_artifacts[{index}].repository_revision must be a full lowercase Git commit SHA, optionally suffixed with +worktree"
                )
            elif artifact_root is not None and not repository_revision_exists(cast(str, repository_revision), artifact_root):
                errors.append(f"supporting_artifacts[{index}].repository_revision must reference a commit in the artifact repository")
        if artifact_root is not None:
            validate_supporting_artifact_path(artifact, artifact_root, errors, index)


def validate_causal_evidence(causal: Any, errors: list[str], *, artifact_root: Path | None = None) -> None:
    if not isinstance(causal, dict):
        errors.append("causal must be an object")
        return

    if causal.get("mode") not in CAUSAL_MODES:
        errors.append("causal.mode must be lite or full")
    require_string(causal, "symptom", errors)
    require_string(causal, "discriminating_check", errors)
    if causal.get("conclusion") not in CAUSAL_CONCLUSIONS:
        errors.append("causal.conclusion must be root_cause_fix, mitigation, instrumentation_only, or unknown")
    if causal.get("confidence") not in CAUSAL_CONFIDENCE:
        errors.append("causal.confidence must be low, medium, or high")
    if causal.get("mode") == "full":
        if not is_nonempty_string(causal.get("upstream_path")):
            errors.append("causal.upstream_path must be a non-empty string for full mode")
        if not is_nonempty_string(causal.get("timeline_evidence")):
            errors.append("causal.timeline_evidence must be a non-empty string for full mode")

    if causal.get("conclusion") == "root_cause_fix":
        require_string(causal, "causal_owner", errors)
        counterfactual = causal.get("counterfactual")
        if not isinstance(counterfactual, dict):
            errors.append("causal.counterfactual must be an object for root_cause_fix")
        else:
            for field in ("intervention", "expected_outcome", "observed_outcome"):
                if not is_nonempty_string(counterfactual.get(field)):
                    errors.append(f"causal.counterfactual.{field} must be a non-empty string for root_cause_fix")
            controlled_factors = counterfactual.get("controlled_factors")
            if not isinstance(controlled_factors, list) or not controlled_factors or any(
                not is_nonempty_string(item) for item in controlled_factors
            ):
                errors.append("causal.counterfactual.controlled_factors must be a non-empty list of non-empty strings")

    evidence_artifacts = causal.get("evidence_artifacts")
    artifact_ids: set[str] = set()
    artifact_kinds: dict[str, str] = {}
    if not isinstance(evidence_artifacts, list) or not evidence_artifacts:
        errors.append("causal.evidence_artifacts must be a non-empty list")
    else:
        for index, artifact in enumerate(evidence_artifacts):
            if not isinstance(artifact, dict):
                errors.append(f"causal.evidence_artifacts[{index}] must be an object")
                continue
            artifact_id = artifact.get("id")
            if not is_nonempty_string(artifact_id):
                errors.append(f"causal.evidence_artifacts[{index}].id must be a non-empty string")
            elif artifact_id in artifact_ids:
                errors.append(f"causal.evidence_artifacts[{index}].id must be unique")
            else:
                artifact_id_string = cast(str, artifact_id)
                artifact_ids.add(artifact_id_string)
                if isinstance(artifact.get("kind"), str):
                    artifact_kinds[artifact_id_string] = artifact["kind"]
            if artifact.get("kind") not in CAUSAL_ARTIFACT_KINDS:
                errors.append(
                    f"causal.evidence_artifacts[{index}].kind must be command_output, diff, test_output, test_source, or trace_export"
                )
            require_string(artifact, "path", errors)
            if not is_sha256(artifact.get("sha256")):
                errors.append(f"causal.evidence_artifacts[{index}].sha256 must be a lowercase SHA-256 digest")
            require_string(artifact, "summary", errors)
            if artifact_root is not None:
                validate_causal_artifact_path(artifact, artifact_root, errors, index)

    evidence_types = causal.get("evidence_types")
    if not isinstance(evidence_types, list) or not evidence_types:
        errors.append("causal.evidence_types must be a non-empty list")
    elif any(item not in CAUSAL_EVIDENCE_TYPES for item in evidence_types):
        errors.append("causal.evidence_types must contain only observational, reproduction, or intervention")

    hypotheses = causal.get("hypotheses")
    if not isinstance(hypotheses, list) or not hypotheses:
        errors.append("causal.hypotheses must be a non-empty list")
    else:
        supported_with_execution_evidence = False
        rejected_or_unresolved_hypothesis = False
        for index, hypothesis in enumerate(hypotheses):
            if not isinstance(hypothesis, dict):
                errors.append(f"causal.hypotheses[{index}] must be an object")
                continue
            for field in ("id", "claim", "prediction"):
                if not is_nonempty_string(hypothesis.get(field)):
                    errors.append(f"causal.hypotheses[{index}].{field} must be a non-empty string")
            if hypothesis.get("status") not in CAUSAL_HYPOTHESIS_STATUSES:
                errors.append(f"causal.hypotheses[{index}].status must be supported, rejected, or unresolved")
            elif hypothesis.get("status") in {"rejected", "unresolved"}:
                rejected_or_unresolved_hypothesis = True
            references = hypothesis.get("evidence_refs")
            if not isinstance(references, list) or any(not is_nonempty_string(item) for item in references):
                errors.append(f"causal.hypotheses[{index}].evidence_refs must be a list of non-empty strings")
                continue
            unknown_references = set(references).difference(artifact_ids)
            if unknown_references:
                errors.append(f"causal.hypotheses[{index}].evidence_refs must name declared evidence artifacts")
            elif hypothesis.get("status") == "supported" and references:
                if any(artifact_kinds.get(reference) in CAUSAL_EXECUTION_ARTIFACT_KINDS for reference in references):
                    supported_with_execution_evidence = True

        if causal.get("conclusion") == "root_cause_fix" and not supported_with_execution_evidence:
            errors.append("causal.root_cause_fix requires a supported hypothesis with execution evidence")
        if causal.get("conclusion") == "root_cause_fix" and not rejected_or_unresolved_hypothesis:
            errors.append("causal.root_cause_fix requires a rejected or unresolved alternative hypothesis")

    if causal.get("conclusion") == "root_cause_fix" and isinstance(evidence_types, list):
        if not {"reproduction", "intervention"}.intersection(evidence_types):
            errors.append("causal.root_cause_fix requires reproduction or intervention evidence")


def validate_evidence(
    data: Any,
    *,
    expected_change_id: str | None = None,
    artifact_root: Path | None = None,
) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["root value must be an object"]

    schema_version = data.get("schema_version")
    if schema_version not in SUPPORTED_SCHEMA_VERSIONS:
        errors.append("schema_version must be 1 or 2")
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

    supporting_artifacts = data.get("supporting_artifacts")
    supporting_artifact_kinds: dict[str, str] = {}
    supporting_artifact_commands: dict[str, str] = {}
    supporting_artifact_exit_codes: dict[str, int] = {}
    if isinstance(supporting_artifacts, list):
        for artifact in supporting_artifacts:
            if not isinstance(artifact, dict):
                continue
            artifact_id = artifact.get("id")
            artifact_kind = artifact.get("kind")
            if not isinstance(artifact_id, str) or not isinstance(artifact_kind, str):
                continue
            supporting_artifact_kinds[artifact_id] = artifact_kind
            command = artifact.get("command")
            exit_code = artifact.get("exit_code")
            if isinstance(command, str):
                supporting_artifact_commands[artifact_id] = command
            if isinstance(exit_code, int) and not isinstance(exit_code, bool):
                supporting_artifact_exit_codes[artifact_id] = exit_code

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
            if schema_version == 2 and item.get("status") == "passed":
                references_value = item.get("evidence_refs")
                if not isinstance(references_value, list) or not references_value or any(
                    not is_nonempty_string(reference) for reference in references_value
                ):
                    errors.append(f"verification[{index}].evidence_refs must be a non-empty list for passed schema_version 2 checks")
                else:
                    references = cast(list[str], references_value)
                    unknown_references = set(references).difference(supporting_artifact_kinds)
                    if unknown_references:
                        errors.append(f"verification[{index}].evidence_refs must name declared supporting artifacts")
                    elif not any(
                        supporting_artifact_kinds[reference] in VERIFICATION_ARTIFACT_KINDS for reference in references
                    ):
                        errors.append(f"verification[{index}].evidence_refs must include command_output or test_output evidence")
                    elif not any(
                        supporting_artifact_kinds[reference] in VERIFICATION_ARTIFACT_KINDS
                        and supporting_artifact_commands.get(reference) == item.get("command")
                        and supporting_artifact_exit_codes.get(reference) == 0
                        for reference in references
                    ):
                        errors.append(
                            f"verification[{index}].evidence_refs must include successful output bound to the same command"
                        )
        if not any(item.get("status") == "passed" for item in verification if isinstance(item, dict)):
            errors.append("verification must contain at least one passed result")

    if level == 2:
        require_string(data, "rollback_or_compatibility", errors)
        review = data.get("independent_review")
        if not isinstance(review, dict):
            errors.append("independent_review must be an object for level 2")
        else:
            require_string(review, "reviewer", errors)
            reviewer = review.get("reviewer")
            if isinstance(reviewer, str) and normalized_reviewer(reviewer) in NON_INDEPENDENT_REVIEWERS:
                errors.append("independent_review.reviewer must identify a reviewer independent from the implementer")
            if review.get("outcome") not in REVIEW_OUTCOMES:
                errors.append("independent_review.outcome must be approved")
            require_string(review, "notes", errors)
            if schema_version == 2:
                review_reference = review.get("evidence_ref")
                if not is_nonempty_string(review_reference):
                    errors.append("independent_review.evidence_ref must be a non-empty string for schema_version 2")
                elif supporting_artifact_kinds.get(cast(str, review_reference)) != "review_report":
                    errors.append("independent_review.evidence_ref must name a review_report supporting artifact")

    if schema_version == 2 and "quality_decisions" not in data:
        errors.append("quality_decisions is required for schema_version 2")
    if "quality_decisions" in data:
        validate_quality_decisions(data["quality_decisions"], errors)

    if schema_version == 2 and "supporting_artifacts" not in data:
        errors.append("supporting_artifacts is required for schema_version 2")
    if "supporting_artifacts" in data:
        validate_supporting_artifacts(
            data["supporting_artifacts"],
            errors,
            artifact_root=artifact_root,
            require_execution_metadata=bool(schema_version == 2),
        )

    if "causal" in data:
        validate_causal_evidence(data["causal"], errors, artifact_root=artifact_root)

    return errors


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as source:
        return json.load(source)


def is_evidence_artifact(path: Path) -> bool:
    return path.parent.name == "evidence" and path.parent.parent.name == ".adam"


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Adam's Development Habits evidence artifacts.")
    parser.add_argument("artifacts", nargs="+", type=Path, help="JSON evidence artifact paths")
    parser.add_argument("--artifact-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    artifact_root = args.artifact_root.resolve()

    failed = False
    for artifact in args.artifacts:
        try:
            expected_change_id = artifact.stem if is_evidence_artifact(artifact) else None
            errors = validate_evidence(
                load_json(artifact),
                expected_change_id=expected_change_id,
                artifact_root=artifact_root,
            )
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
