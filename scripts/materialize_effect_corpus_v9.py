#!/usr/bin/env python3
"""Materialize the fresh split-tree V9 capability corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import cast


PUBLIC_COMMAND = ["python3", "-m", "unittest", "discover", "-s", "tests"]
CONDITIONS = ("no_skill", "old_skill", "new_skill")
EXPECTED_STRATA = {"single-module": 6, "cross-module": 8, "integration": 6}
EXPECTED_COHORTS = {"decision-retention": 20, "repair": 20}
Case = tuple[tuple[object, ...], object]


@dataclass(frozen=True)
class TaskSpec:
    task_id: str
    cohort: str
    stratum: str
    description: str
    signature: str
    buggy_body: str
    fixed_body: str
    public_cases: tuple[Case, ...]
    hidden_cases: tuple[Case, ...]


def body(value: str) -> str:
    return textwrap.dedent(value).strip()


def source(signature: str, implementation: str) -> str:
    return f"def evaluate({signature}):\n{textwrap.indent(body(implementation), '    ')}\n"


def cases(*values: Case) -> tuple[Case, ...]:
    return values


def test_source(test_cases: tuple[Case, ...], class_name: str) -> str:
    return (
        "import unittest\nfrom policy import evaluate\n\n"
        f"CASES = {test_cases!r}\n\n"
        f"class {class_name}(unittest.TestCase):\n"
        "    def test_contract(self):\n"
        "        for arguments, expected in CASES:\n"
        "            with self.subTest(arguments=arguments):\n"
        "                self.assertEqual(evaluate(*arguments), expected)\n"
    )


def spec(
    task_id: str,
    cohort: str,
    stratum: str,
    description: str,
    signature: str,
    buggy_body: str,
    fixed_body: str,
    public_cases: tuple[Case, ...],
    hidden_cases: tuple[Case, ...],
) -> TaskSpec:
    return TaskSpec(
        task_id,
        cohort,
        stratum,
        description.strip() + "\n",
        signature,
        buggy_body,
        fixed_body,
        public_cases,
        hidden_cases,
    )


def decision_tasks() -> list[TaskSpec]:
    rows = [
        ("claim_state_machine", "single-module", "Return planned, executed, or verified without promoting an unrun claim.", "command_ran, acceptance_met", "return 'verified' if acceptance_met else 'planned'", "return 'planned' if not command_ran else ('verified' if acceptance_met else 'executed')", cases(((False, True), "planned")), cases(((False, False), "planned"), ((True, False), "executed"), ((True, True), "verified"))),
        ("unknown_write_reconciliation", "single-module", "Choose the safe action for FOUND, ABSENT, or UNKNOWN remote-write reconciliation.", "state", "return 'finalize' if state == 'FOUND' else 'resend'", "return {'FOUND': 'finalize', 'ABSENT': 'resend', 'UNKNOWN': 'preserve_pending'}[state]", cases((("UNKNOWN",), "preserve_pending")), cases((("FOUND",), "finalize"), (("ABSENT",), "resend"))),
        ("preacceptance_retry_gate", "single-module", "Retry only an idempotent operation rejected before acceptance with a retryable classification.", "accepted, rejection, idempotent", "return rejection in {'transient', 'retryable_preacceptance'}", "return (not accepted) and rejection == 'retryable_preacceptance' and idempotent", cases(((True, "retryable_preacceptance", True), False)), cases(((False, "retryable_preacceptance", True), True), ((False, "transient", True), False), ((False, "retryable_preacceptance", False), False))),
        ("causal_conclusion_gate", "single-module", "Do not claim a root-cause fix without an executed intervention that removes the reproduction.", "intervention_executed, reproduction_removed", "return 'root-cause fix' if reproduction_removed else 'unknown'", "return 'root-cause fix' if intervention_executed and reproduction_removed else 'unknown'", cases(((False, True), "unknown")), cases(((True, True), "root-cause fix"), ((True, False), "unknown"), ((False, False), "unknown"))),
        ("bounded_retry_budget", "single-module", "Enforce attempt, transient, and idempotency gates for retries.", "attempt, max_attempts, transient, idempotent", "return transient", "return transient and idempotent and attempt < max_attempts", cases(((3, 3, True, True), False)), cases(((2, 3, True, True), True), ((1, 3, False, True), False), ((1, 3, True, False), False))),
        ("low_risk_level", "single-module", "Classify no-behavior, ordinary behavior, and public-contract changes without always escalating.", "behavior_change, public_contract", "return 2", "return 0 if not behavior_change else (2 if public_contract else 1)", cases(((False, False), 0)), cases(((True, False), 1), ((True, True), 2))),
        ("migration_contract_gate", "cross-module", "Contract only after consumers are ready and the backfill error rate meets its bound.", "consumers_ready, error_rate, limit", "return 'contract' if error_rate <= limit else 'migrate'", "return 'contract' if consumers_ready and error_rate <= limit else 'migrate'", cases(((False, 0.0, 0.01), "migrate")), cases(((True, 0.0, 0.01), "contract"), ((True, 0.02, 0.01), "migrate"))),
        ("flag_rollback_sequence", "cross-module", "Disable the feature flag before reverting deployed code.", "flag_exists", "return ('revert_code', 'disable_flag') if flag_exists else ('revert_code',)", "return ('disable_flag', 'revert_code') if flag_exists else ('revert_code',)", cases(((True,), ("disable_flag", "revert_code"))), cases(((False,), ("revert_code",)))),
        ("red_ci_merge_gate", "cross-module", "Never merge a red required CI result.", "ci_green", "return True", "return bool(ci_green)", cases(((False,), False)), cases(((True,), True))),
        ("dirty_worktree_scope", "cross-module", "Select only task-owned paths from a dirty worktree.", "changed_paths, task_paths", "return tuple(changed_paths)", "return tuple(path for path in changed_paths if path in set(task_paths))", cases(((('owner.py', 'notes.txt'), ('owner.py',)), ('owner.py',))), cases(((('other.py',), ('owner.py',)), ()))),
        ("secret_rotation_readiness", "cross-module", "Require redaction, owner, access review, and expiry before declaring rotation ready.", "redacted, owner, access_reviewed, expiry_set", "return redacted", "return redacted and bool(owner) and access_reviewed and expiry_set", cases(((True, "", True, True), False)), cases(((True, "security", True, True), True), ((False, "security", True, True), False))),
        ("dependency_release_readiness", "cross-module", "Require advisory, lockfile, compatibility, and rollback evidence for a dependency change.", "advisory, lockfile, compatibility, rollback", "return compatibility", "return advisory and lockfile and compatibility and rollback", cases(((False, True, True, True), False)), cases(((True, True, True, True), True), ((True, False, True, True), False))),
        ("runbook_recovery_owner", "cross-module", "Require diagnosis, recovery, rollback, and an owner in the runbook.", "diagnosis, recovery, rollback, owner", "return diagnosis and recovery", "return diagnosis and recovery and rollback and bool(owner)", cases(((True, True, False, "ops"), False)), cases(((True, True, True, "ops"), True), ((True, True, True, ""), False))),
        ("clean_reproduction_gate", "cross-module", "Require a non-secret fixture, clean environment, and discovered repository tools.", "fixture_has_secret, clean_environment, tools_discovered", "return clean_environment", "return (not fixture_has_secret) and clean_environment and tools_discovered", cases(((True, True, True), False)), cases(((False, True, True), True), ((False, False, True), False))),
        ("production_authority_gate", "integration", "Allow production action only with explicit authorization while keeping local work available.", "environment, authorized", "return environment == 'production'", "return environment != 'production' or authorized", cases((("production", False), False)), cases((("production", True), True), (("local", False), True))),
        ("unknown_ack_handoff", "integration", "Acknowledge confirmed work or unknown work only after durable recovery handoff.", "state, recovery_scheduled", "return state == 'FOUND' or recovery_scheduled", "return state == 'FOUND' or (state == 'UNKNOWN' and recovery_scheduled)", cases((("ABSENT", True), False)), cases((("FOUND", False), True), (("UNKNOWN", True), True), (("UNKNOWN", False), False))),
        ("canonical_identity_match", "integration", "Match every side-effect-defining identity dimension before finalization.", "event_match, tenant_match, payload_match", "return event_match", "return event_match and tenant_match and payload_match", cases(((True, False, True), False)), cases(((True, True, True), True), ((False, True, True), False))),
        ("terminal_rejection_state", "integration", "Persist terminal rejection as failed and never revive it as retryable.", "terminal", "return 'retry'", "return 'failed' if terminal else 'pending'", cases(((True,), "failed")), cases(((False,), "pending"))),
        ("backfill_stop_signal", "integration", "Stop a backfill when error rate or replication lag exceeds its concrete bound.", "error_rate, error_limit, lag_seconds, lag_limit", "return 'stop' if error_rate > error_limit else 'continue'", "return 'stop' if error_rate > error_limit or lag_seconds > lag_limit else 'continue'", cases(((0.0, 0.01, 45, 30), "stop")), cases(((0.0, 0.01, 20, 30), "continue"), ((0.02, 0.01, 20, 30), "stop"))),
        ("flag_default_state", "integration", "Keep a new feature disabled until an explicit approved enablement stage.", "stage", "return True", "return stage == 'approved_enablement'", cases((("deploy",), False)), cases((("approved_enablement",), True), (("rollback",), False))),
    ]
    return [spec(task_id, "decision-retention", stratum, description, signature, buggy, fixed, public, hidden) for task_id, stratum, description, signature, buggy, fixed, public, hidden in rows]


def repair_tasks() -> list[TaskSpec]:
    rows = [
        ("casefold_header_lookup", "single-module", "HTTP header lookup must be ASCII-case-insensitive.", "headers, name", "return headers.get(name)", "return next((value for key, value in headers.items() if key.lower() == name.lower()), None)", cases((({"content-type": "json"}, "Content-Type"), "json")), cases((({"X-ID": "7"}, "x-id"), "7"), (({}, "x"), None))),
        ("currency_scale_conversion", "single-module", "Convert minor currency units using the declared scale instead of assuming cents.", "minor, scale", "return minor / 100", "return minor / (10 ** scale)", cases(((1234, 3), 1.234)), cases(((1234, 2), 12.34), ((5, 0), 5.0))),
        ("path_segment_boundary", "single-module", "A route prefix matches a complete path segment, not an arbitrary string prefix.", "path, prefix", "return path.startswith(prefix)", "return path == prefix or path.startswith(prefix.rstrip('/') + '/')", cases((("/administer", "/admin"), False)), cases((("/admin/users", "/admin"), True), (("/admin", "/admin"), True))),
        ("offset_day_rollover", "single-module", "Normalize an hour offset while retaining the day rollover.", "hour", "return (0, hour % 24)", "return divmod(hour, 24)", cases(((-1,), (-1, 23))), cases(((25,), (1, 1)), ((0,), (0, 0)))),
        ("stable_event_order", "single-module", "Sort event pairs chronologically while preserving input order for equal timestamps.", "records", "return tuple(name for _, name in sorted(records, reverse=True))", "return tuple(name for _, name in sorted(records, key=lambda item: item[0]))", cases(((((2, "b"), (1, "a")),), ("a", "b"))), cases(((((1, "a"), (1, "b")),), ("a", "b")))),
        ("tenant_cache_partition", "single-module", "Partition cache keys by tenant and logical key.", "tenant, key", "return key", "return (tenant, key)", cases((("tenant-a", "profile"), ("tenant-a", "profile"))), cases((("tenant-b", "profile"), ("tenant-b", "profile")))),
        ("raw_signature_payload", "cross-module", "Preserve exact request bytes for signature verification.", "payload", "return payload.decode('utf-8').strip().encode('utf-8')", "return payload", cases(((b' {"x":1}\n',), b' {"x":1}\n')), cases(((b"abc",), b"abc"))),
        ("one_based_pagination", "cross-module", "Slice pages using a one-based public page number.", "items, page, size", "start = page * size\nreturn tuple(items[start:start + size])", "start = (page - 1) * size\nreturn tuple(items[start:start + size])", cases((((1, 2, 3, 4), 1, 2), (1, 2))), cases((((1, 2, 3, 4), 2, 2), (3, 4)))),
        ("composite_delivery_dedupe", "cross-module", "Deduplicate delivery by tenant and event, not event alone.", "tenant, event_id", "return event_id", "return (tenant, event_id)", cases((("tenant-a", "evt-1"), ("tenant-a", "evt-1"))), cases((("tenant-b", "evt-1"), ("tenant-b", "evt-1")))),
        ("address_snapshot_copy", "cross-module", "Keep an order address snapshot independent from later profile mutation.", "address, new_city", "saved = address\naddress['city'] = new_city\nreturn (saved['city'], address['city'])", "saved = dict(address)\naddress['city'] = new_city\nreturn (saved['city'], address['city'])", cases((({"city": "A"}, "B"), ("A", "B"))), cases((({"city": "X"}, "Y"), ("X", "Y")))),
        ("reservation_compensation", "cross-module", "Restore reserved stock when the downstream payment does not succeed.", "stock, requested, payment_ok", "return stock - requested", "return stock - requested if payment_ok else stock", cases(((10, 3, False), 10)), cases(((10, 3, True), 7))),
        ("email_identity_normalization", "cross-module", "Normalize email identity with surrounding whitespace and Unicode-safe case folding.", "email", "return email.lower()", "return email.strip().casefold()", cases((("  User@Example.COM ",), "user@example.com")), cases((("Straße@EXAMPLE.COM",), "strasse@example.com"))),
        ("retryable_http_classes", "cross-module", "Retry only explicitly transient HTTP outcomes.", "status", "return status >= 400", "return status in {408, 429, 500, 502, 503, 504}", cases(((404,), False)), cases(((503,), True), ((401,), False), ((429,), True))),
        ("required_permission_set", "cross-module", "Require every permission in the operation contract.", "grants, required", "return bool(set(grants) & set(required))", "return set(required).issubset(set(grants))", cases(((('read',), ('read', 'write')), False)), cases(((('read', 'write'), ('read', 'write')), True))),
        ("configuration_precedence", "integration", "Preserve falsey values while applying environment, file, then default precedence.", "default, file_value, env_value", "return env_value or file_value or default", "return env_value if env_value is not None else (file_value if file_value is not None else default)", cases((("on", "file", ""), "")), cases((("on", "", None), ""), (("on", None, None), "on"))),
        ("outbox_commit_visibility", "integration", "Publish only when both the business commit and durable outbox event exist.", "business_committed, outbox_written", "return outbox_written", "return business_committed and outbox_written", cases(((False, True), False)), cases(((True, True), True), ((True, False), False))),
        ("session_rotation_revocation", "integration", "Issuing a replacement session must invalidate the previous session.", "new_issued", "return (new_issued, True)", "return (new_issued, not new_issued)", cases(((True,), (True, False))), cases(((False,), (False, True)))),
        ("lock_release_on_failure", "integration", "Release a pipeline lock on both success and failure.", "raises", "return True if raises else False", "return False", cases(((True,), False)), cases(((False,), False))),
        ("blob_before_manifest", "integration", "Advance a manifest only after the referenced blob is durable.", "blob_written", "return True", "return bool(blob_written)", cases(((False,), False)), cases(((True,), True))),
        ("authorization_cache_identity", "integration", "Partition authorization cache entries by tenant, user, and resource.", "tenant, user, resource", "return (user, resource)", "return (tenant, user, resource)", cases((("tenant-a", "u1", "doc"), ("tenant-a", "u1", "doc"))), cases((("tenant-b", "u1", "doc"), ("tenant-b", "u1", "doc")))),
    ]
    return [spec(task_id, "repair", stratum, description, signature, buggy, fixed, public, hidden) for task_id, stratum, description, signature, buggy, fixed, public, hidden in rows]


def make_tasks() -> list[TaskSpec]:
    return decision_tasks() + repair_tasks()


def tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(relative + b"\0" + hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def write_tree(root: Path, files: dict[str, str]) -> None:
    for relative, content in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        _ = path.write_text(content, encoding="utf-8")


def materialize(corpus: Path) -> dict[str, object]:
    tasks = make_tasks()
    if corpus.exists():
        raise FileExistsError(f"refusing to overwrite existing corpus: {corpus}")
    if len(tasks) != 40 or len({task.task_id for task in tasks}) != 40:
        raise ValueError("V9 corpus must contain 40 unique tasks")
    for cohort, expected_count in EXPECTED_COHORTS.items():
        cohort_tasks = [task for task in tasks if task.cohort == cohort]
        if len(cohort_tasks) != expected_count:
            raise ValueError(f"V9 cohort {cohort} count mismatch")
        counts = {stratum: sum(task.stratum == stratum for task in cohort_tasks) for stratum in EXPECTED_STRATA}
        if counts != EXPECTED_STRATA:
            raise ValueError(f"V9 cohort {cohort} strata mismatch: {counts}")

    manifest_tasks: list[dict[str, object]] = []
    for task in tasks:
        public_root = corpus / "tasks" / task.task_id
        hidden_root = corpus / "hidden-tests" / task.task_id
        reference_root = corpus / "references" / task.task_id
        public_test = test_source(task.public_cases, "PublicContract")
        hidden_test = test_source(task.hidden_cases, "HiddenContract")
        buggy = source(task.signature, task.buggy_body)
        fixed = source(task.signature, task.fixed_body)
        write_tree(public_root, {"policy.py": buggy, "task.md": task.description, "tests/test_public.py": public_test})
        write_tree(hidden_root, {"tests/test_hidden.py": hidden_test})
        write_tree(reference_root, {"policy.py": fixed, "task.md": task.description, "tests/test_public.py": public_test, "tests/test_hidden.py": hidden_test})
        manifest_tasks.append({
            "task_id": task.task_id,
            "cohort": task.cohort,
            "stratum": task.stratum,
            "workspace_path": f"tasks/{task.task_id}",
            "hidden_tests_path": f"hidden-tests/{task.task_id}",
            "reference_path": f"references/{task.task_id}",
            "allowed_edit_paths": ["policy.py"],
            "public_command": PUBLIC_COMMAND,
            "hidden_command": PUBLIC_COMMAND,
            "workspace_tree_sha256": tree_digest(public_root),
            "hidden_tests_tree_sha256": tree_digest(hidden_root),
            "reference_tree_sha256": tree_digest(reference_root),
        })

    manifest = cast(dict[str, object], {
        "schema_version": 2,
        "corpus_id": "effect-corpus-v9",
        "generated_by": "scripts/materialize_effect_corpus_v9.py",
        "task_count": len(tasks),
        "cohorts": EXPECTED_COHORTS,
        "strata_per_cohort": EXPECTED_STRATA,
        "conditions": CONDITIONS,
        "split": {
            "public_workspace_excludes_hidden_tests": True,
            "hidden_tree_contains_tests_only": True,
            "reference_tree_is_validation_only": True,
            "hidden_tests_are_injected_after_agent_exit": True,
        },
        "tasks": manifest_tasks,
    })
    corpus.mkdir(parents=True, exist_ok=True)
    _ = (corpus / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    _ = parser.add_argument("--corpus", type=Path, required=True)
    arguments = cast(dict[str, object], vars(parser.parse_args()))
    _ = materialize(cast(Path, arguments["corpus"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
