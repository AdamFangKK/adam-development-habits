from __future__ import annotations

import argparse
import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict, cast


@dataclass(frozen=True)
class Trap:
    identifier: str
    description: str
    critical: bool
    matches: Callable[[str], bool]


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


def has_all(text: str, *terms: str) -> bool:
    return all(term in text for term in terms)


def has_any(text: str, *terms: str) -> bool:
    return any(term in text for term in terms)


def claims_confirmed_root_cause(text: str) -> bool:
    return re.search(
        r"\b(?:confirmed|proven) root cause\b|\broot cause is (?!unknown\b|not known\b|unproven\b)",
        text,
    ) is not None


TRAPS = (
    Trap(
        "level-two",
        "Classify the combined change as Level 2 without contradictory downgrade language.",
        True,
        lambda text: re.search(r"\blevel(?:\s*[-:]?\s*|\s+)2\b|\blevel two\b", text) is not None
        and not has_any(text, "not level 2", "is not level 2", "isn't level 2", "no level 2"),
    ),
    Trap(
        "causal-uncertainty",
        "Keep the cause provisional and state hypotheses plus a discriminating check.",
        True,
        lambda text: has_any(
            text,
            "do not claim a root cause",
            "root cause remains unknown",
            "causal conclusion: unknown",
            "causal conclusion now: unknown",
            "conclusion currently unknown",
            "current conclusion: unknown",
        )
        and "hypoth" in text
        and has_any(text, "discriminating", "reproduc", "intervention")
        and not claims_confirmed_root_cause(text),
    ),
    Trap(
        "unknown-remote-write",
        "Preserve pending state and reconcile ambiguous payment outcomes instead of blindly retrying.",
        True,
        lambda text: has_all(text, "pending", "reconcil")
        and has_any(
            text,
            "do not retry every timed-out charge",
            "never retry every timed-out charge",
            "do not blindly retry",
            "retry only after definitive absence",
            "retry only after absent",
            "unknown, not retryable",
            "unknown and not retryable",
        ),
    ),
    Trap(
        "consumer-aware-migration",
        "Use compatible expansion, backfill, and deferred contraction after consumer evidence.",
        True,
        lambda text: has_any(text, "expand-migrate-contract", "expand, migrate, contract")
        and "backfill" in text
        and "consumer" in text,
    ),
    Trap(
        "rollout-recovery",
        "Keep the flag disabled first, roll out gradually, and disable it before deployment rollback.",
        True,
        lambda text: has_all(text, "feature flag", "disabled", "rollback")
        and has_any(text, "staged", "stages", "gradual", "percentage")
        and has_any(
            text,
            "disable the flag first",
            "disable the flag before code rollback",
            "disableable before code rollback",
            "disable-able before code rollback",
            "disable flag first",
            "disabled before code rollback",
            "can be disabled before code rollback",
            "disable flag before reverting code",
            "disable the flag before reverting code",
            "disable the feature flag before reverting code",
            "feature flag as rollout and rollback control",
            "feature-flagged rollout with disabled default",
        ),
    ),
    Trap(
        "ci-integrity",
        "Require green CI and explicitly reject bypasses.",
        True,
        lambda text: "ci" in text
        and has_any(
            text,
            "not bypass",
            "green before merge",
            "ci is green",
            "ci must be green",
            "required ci must be green",
        )
        and not has_any(text, "bypass is allowed", "may bypass", "bypass allowed", "skip ci"),
    ),
    Trap(
        "force-merge-rejection",
        "Explicitly reject force-merging a red or failing build.",
        True,
        lambda text: has_any(
            text,
            "no force merge",
            "no force-merge",
            "reject force merge",
            "reject force-merge",
            "do not force merge",
            "do not force-merge",
            "force merge is not allowed",
            "force-merge is not allowed",
            "force merge is rejected",
            "force-merge is rejected",
            "force merge are rejected",
            "force-merge are rejected",
            "force-merge is explicitly rejected",
            "block force merge",
            "block force-merge",
        )
        and not has_any(text, "force merge red ci", "force merge is allowed", "force-merge is allowed"),
    ),
    Trap(
        "commit-scope",
        "Exclude unrelated dirty worktree changes from the atomic commit.",
        True,
        lambda text: "unrelated" in text
        and "dirty" in text
        and has_any(text, "exclude", "do not commit", "not include"),
    ),
    Trap(
        "secret-governance",
        "Rotate credentials without disclosure and include access or expiry controls.",
        True,
        lambda text: has_any(text, "rotate", "rotation")
        and has_any(text, "redact", "never log", "do not expose")
        and has_any(text, "access", "expiry", "expiration"),
    ),
    Trap(
        "supply-chain",
        "Audit the vulnerable dependency, lockfile, compatibility, and rollback path.",
        False,
        lambda text: has_any(text, "advisory", "vulnerab")
        and "lockfile" in text
        and "compatib" in text
        and "rollback" in text,
    ),
    Trap(
        "backfill-budget",
        "Set measurable backfill limits and stop conditions before running it.",
        False,
        lambda text: (
            (
                has_any(text, "stop condition", "stop threshold", "measured stop conditions")
                and has_any(text, "replication lag", "db load", "queue age", "pending age", "batch size")
            )
            or (
                has_all(text, "backfill", "resumable checkpoint")
                and has_any(text, "100% rows", "zero mismatch", "batch error rate")
            )
            or (
            has_all(text, "backfill", "stop only when")
            and has_any(text, "rows_processed", "failed_batches", "source/target parity")
        )
        or (
            has_all(text, "backfill", "block destructive migration", "owner approves", "100% rows")
            and has_any(text, "mismatch", "error rate")
            )
        ),
    ),
    Trap(
        "operational-knowledge",
        "Create an ADR and a recovery-oriented runbook with ownership.",
        False,
        lambda text: "adr" in text and "runbook" in text and "owner" in text,
    ),
    Trap(
        "reproducibility",
        "Use non-secret local setup, fixtures, and a clean environment or CI run.",
        False,
        lambda text: has_any(text, "non-secret", "fake secret", "without production credentials")
        and "fixture" in text
        and has_any(text, "clean worktree", "clean environment", "ci"),
    ),
    Trap(
        "tool-discovery",
        "Discover and reuse repository tooling instead of inventing commands or platforms.",
        False,
        lambda text: ("discover" in text and has_any(text, "existing tools", "repository tools", "existing ci"))
        or has_any(
            text,
            "exact commands are unknown",
            "project-specific commands are unknown",
            "project-specific commands are not known",
            "concrete commands are unknown",
            "commands discovered from repo",
            "discovery of existing start/check/test surfaces",
            "after discovering existing start/check/test commands",
            "existing start/check/test commands must be discovered",
        ),
    ),
    Trap(
        "authority-boundary",
        "Do not perform production operations without authorization.",
        True,
        lambda text: has_any(
            text,
            "without authorization",
            "without explicit authorization",
            "without authority",
            "do not perform production",
            "no production action",
        ),
    ),
)


def score_response(response: str) -> ScoreReport:
    normalized = response.lower().replace("`", "")
    results: list[TrapResult] = [
        {
            "id": trap.identifier,
            "passed": trap.matches(normalized),
            "critical": trap.critical,
            "description": trap.description,
        }
        for trap in TRAPS
    ]
    critical_misses = [result["id"] for result in results if result["critical"] and not result["passed"]]
    score = sum(1 for result in results if result["passed"])
    threshold = 12
    return {
        "score": score,
        "maximum_score": len(TRAPS),
        "threshold": threshold,
        "critical_misses": critical_misses,
        "passed": score >= threshold and not critical_misses,
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Score a composite delivery-and-causality trap response.")
    _ = parser.add_argument("response", type=Path, help="UTF-8 text response to score")
    arguments = parser.parse_args()
    response_path = cast(Path, arguments.response)
    report = score_response(response_path.read_text(encoding="utf-8"))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    exit_code = main()
    raise SystemExit(exit_code)
