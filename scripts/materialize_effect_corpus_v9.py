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


@dataclass(frozen=True)
class CleanupSpec:
    task_id: str
    cohort: str
    stratum: str
    description: str
    kind: str
    signature: str
    buggy_source: str
    fixed_source: str
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


def cleanup_hidden_test(task_id: str, kind: str, hidden_cases: tuple[Case, ...]) -> str:
    cases = repr(hidden_cases)
    legacy_name = f"legacy_{task_id}"
    duplicate_name = f"new_duplicate_{task_id}"
    if kind == "retain":
        hygiene = (
            f"        self.assertIn('external_adapter_{task_id}', source)\n"
            "        self.assertIn('EXTERNAL_REGISTRY', source)\n"
            f"        self.assertNotIn('stale compatibility note {task_id}', source)\n"
            f"        self.assertTrue(Path('adapters/{task_id}.py').is_file())\n"
            f"        self.assertTrue(Path('runtime/{task_id}.json').is_file())\n"
            f"        self.assertNotIn('old contract {task_id}', Path('README.md').read_text(encoding='utf-8'))\n"
        )
    elif kind == "duplicate":
        hygiene = (
            f"        self.assertNotIn('{duplicate_name}', source)\n"
            f"        self.assertFalse(Path('helpers/{task_id}_duplicate.py').exists())\n"
            f"        self.assertNotIn('old contract {task_id}', Path('README.md').read_text(encoding='utf-8'))\n"
        )
    elif kind == "docs":
        hygiene = (
            f"        self.assertNotIn('old contract {task_id}', source)\n"
            f"        self.assertIn('Current contract {task_id}', source)\n"
            f"        self.assertNotIn('old contract {task_id}', Path('README.md').read_text(encoding='utf-8'))\n"
            f"        self.assertIn('Current contract {task_id}', Path('docs/{task_id}.md').read_text(encoding='utf-8'))\n"
        )
    else:
        hygiene = (
            f"        self.assertNotIn('{legacy_name}', source)\n"
            "        self.assertNotIn('Legacy path retained', source)\n"
            f"        self.assertFalse(Path('legacy/{task_id}.py').exists())\n"
            f"        self.assertFalse(Path('config/{task_id}.toml').exists())\n"
            f"        self.assertNotIn('old contract {task_id}', Path('README.md').read_text(encoding='utf-8'))\n"
        )
    return (
        "from pathlib import Path\n"
        "import unittest\n\n"
        "from policy import evaluate\n\n"
        f"CASES = {cases}\n\n"
        "class HiddenContract(unittest.TestCase):\n"
        "    def test_current_behavior(self):\n"
        "        for arguments, expected in CASES:\n"
        "            with self.subTest(arguments=arguments):\n"
        "                self.assertEqual(evaluate(*arguments), expected)\n\n"
        "    def test_retirement_hygiene(self):\n"
        "        source = Path('policy.py').read_text(encoding='utf-8')\n"
        f"{hygiene}"
        "\n\nif __name__ == '__main__':\n"
        "    unittest.main()\n"
    )


def cleanup_source(
    task_id: str,
    kind: str,
    signature: str,
    buggy_logic: str,
    fixed_logic: str,
    description: str,
) -> tuple[str, str]:
    legacy_name = f"legacy_{task_id}"
    canonical_name = f"canonical_{task_id}"
    duplicate_name = f"new_duplicate_{task_id}"
    if kind == "retain":
        buggy = f'''"""{description}"""

EXTERNAL_REGISTRY = {{"external_adapter_{task_id}": "{canonical_name}"}}


def external_adapter_{task_id}({signature}):
    return {fixed_logic}


def {canonical_name}({signature}):
    return {fixed_logic}


def evaluate({signature}):
    # stale compatibility note {task_id}
    return {canonical_name}({signature})
'''
        fixed = f'''"""{description}"""

EXTERNAL_REGISTRY = {{"external_adapter_{task_id}": "{canonical_name}"}}


def external_adapter_{task_id}({signature}):
    return {fixed_logic}


def {canonical_name}({signature}):
    return {fixed_logic}


def evaluate({signature}):
    return {canonical_name}({signature})
'''
        return buggy, fixed
    if kind == "duplicate":
        buggy = f'''"""{description}"""


def {canonical_name}({signature}):
    return {fixed_logic}


def {duplicate_name}({signature}):
    return {fixed_logic}


def evaluate({signature}):
    return {duplicate_name}({signature})
'''
        fixed = f'''"""{description}"""


def {canonical_name}({signature}):
    return {fixed_logic}


def evaluate({signature}):
    return {canonical_name}({signature})
'''
        return buggy, fixed
    if kind == "docs":
        buggy = f'''"""old contract {task_id}: legacy normalization remains the default."""


def {canonical_name}({signature}):
    return {fixed_logic}


def evaluate({signature}):
    # old contract {task_id}
    return {canonical_name}({signature})
'''
        fixed = f'''"""Current contract {task_id}: the canonical behavior is maintained here."""


def {canonical_name}({signature}):
    return {fixed_logic}


def evaluate({signature}):
    return {canonical_name}({signature})
'''
        return buggy, fixed
    buggy = f'''"""{description}"""


def {legacy_name}({signature}):
    return {buggy_logic}


def {canonical_name}({signature}):
    return {fixed_logic}


def evaluate({signature}):
    # Legacy path retained while the replacement rolls out.
    return {legacy_name}({signature})
'''
    fixed = f'''"""{description}"""


def {canonical_name}({signature}):
    return {fixed_logic}


def evaluate({signature}):
    return {canonical_name}({signature})
'''
    return buggy, fixed


def cleanup_supporting_files(task_id: str, kind: str, *, fixed: bool) -> dict[str, str]:
    """Add non-code contract surfaces that a real retirement sweep must reconcile."""
    current_readme = f"# Current contract {task_id}\nThe canonical policy is evaluate.\n"
    stale_readme = f"# Current contract {task_id}\nold contract {task_id}: legacy path remains supported.\n"
    current_docs = f"Current contract {task_id}: callers use the canonical policy.\n"
    stale_docs = f"old contract {task_id}: callers use the legacy policy.\n"
    files = {
        "README.md": current_readme if fixed else stale_readme,
        f"docs/{task_id}.md": current_docs if fixed else stale_docs,
    }
    if kind == "replace":
        if not fixed:
            files[f"legacy/{task_id}.py"] = "def legacy_handler(value):\n    return value\n"
            files[f"config/{task_id}.toml"] = f"legacy_flag = \"{task_id}\"\n"
    elif kind == "duplicate":
        if not fixed:
            files[f"helpers/{task_id}_duplicate.py"] = "def duplicate_handler(value):\n    return value\n"
    elif kind == "retain":
        files[f"adapters/{task_id}.py"] = f"def external_adapter_{task_id}(value):\n    return value\n"
        files[f"runtime/{task_id}.json"] = f'{{"EXTERNAL_REGISTRY": "external_adapter_{task_id}"}}\n'
    return files


def cleanup_tasks() -> list[CleanupSpec]:
    strata = ("single-module",) * 6 + ("cross-module",) * 8 + ("integration",) * 6
    logic_rows = (
        ("casefold", "value", "value.strip().lower()", "value.strip().casefold()", ((" Straße@example.com ",), "strasse@example.com"), ((" User@example.com ",), "user@example.com")),
        ("trim", "value", "value", "value.strip()", (("  value  ",), "value"), (("\nvalue\t",), "value")),
        ("segment", "path, prefix", "path.startswith(prefix)", "path == prefix or path.startswith(prefix.rstrip('/') + '/')", (("/administer", "/admin"), False), (("/admin/users", "/admin"), True)),
        ("scale", "minor, scale", "minor / 100", "minor / (10 ** scale)", ((1234, 3), 1.234), ((5, 0), 5.0)),
        ("order", "records", "tuple(name for _, name in sorted(records, reverse=True))", "tuple(name for _, name in sorted(records, key=lambda item: item[0]))", ((((2, "b"), (1, "a")),), ("a", "b")), ((((1, "a"), (1, "b")),), ("a", "b"))),
    )
    specs: list[CleanupSpec] = []
    for index in range(40):
        cohort = "decision-retention" if index < 20 else "repair"
        stratum = strata[index % len(strata)]
        logic_name, signature, buggy_logic, fixed_logic, public_case, hidden_case = logic_rows[index % len(logic_rows)]
        task_id = f"cleanup_{cohort.replace('-', '_')}_{logic_name}_{index + 1:02d}"
        if cohort == "repair":
            kind = "replace"
            description = f"Replace the obsolete {logic_name} implementation with the canonical contract. Keep the public behavior correct and update the implementation in policy.py."
            buggy_source, fixed_source = cleanup_source(task_id, kind, signature, buggy_logic, fixed_logic, description)
            public_cases = (public_case,)
            hidden_cases = (hidden_case,)
        else:
            kind = ("duplicate", "retain", "docs")[index % 3]
            description = f"Update the {logic_name} request policy in policy.py while preserving the existing public contract."
            buggy_source, fixed_source = cleanup_source(task_id, kind, signature, buggy_logic, fixed_logic, description)
            public_cases = (hidden_case,)
            hidden_cases = (hidden_case,)
        specs.append(CleanupSpec(task_id, cohort, stratum, description + "\n", kind, signature, buggy_source, fixed_source, public_cases, hidden_cases))
    return specs


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


def materialize_cleanup(corpus: Path) -> dict[str, object]:
    """Materialize a held-out corpus for automatic retirement and drift cleanup."""
    tasks = cleanup_tasks()
    if corpus.exists():
        raise FileExistsError(f"refusing to overwrite existing corpus: {corpus}")
    if len(tasks) != 40 or len({task.task_id for task in tasks}) != 40:
        raise ValueError("cleanup corpus must contain 40 unique tasks")
    for cohort, expected_count in EXPECTED_COHORTS.items():
        cohort_tasks = [task for task in tasks if task.cohort == cohort]
        if len(cohort_tasks) != expected_count:
            raise ValueError(f"cleanup cohort {cohort} count mismatch")
        counts = {stratum: sum(task.stratum == stratum for task in cohort_tasks) for stratum in EXPECTED_STRATA}
        if counts != EXPECTED_STRATA:
            raise ValueError(f"cleanup cohort {cohort} strata mismatch: {counts}")

    manifest_tasks: list[dict[str, object]] = []
    for task in tasks:
        public_root = corpus / "tasks" / task.task_id
        hidden_root = corpus / "hidden-tests" / task.task_id
        reference_root = corpus / "references" / task.task_id
        public_test = test_source(task.public_cases, "PublicContract")
        hidden_test = cleanup_hidden_test(task.task_id, task.kind, task.hidden_cases)
        public_files = {
            "policy.py": task.buggy_source,
            "task.md": task.description,
            "tests/test_public.py": public_test,
            **cleanup_supporting_files(task.task_id, task.kind, fixed=False),
        }
        reference_files = {
            "policy.py": task.fixed_source,
            "task.md": task.description,
            "tests/test_public.py": public_test,
            "tests/test_hidden.py": hidden_test,
            **cleanup_supporting_files(task.task_id, task.kind, fixed=True),
        }
        write_tree(public_root, public_files)
        write_tree(hidden_root, {"tests/test_hidden.py": hidden_test})
        write_tree(reference_root, reference_files)
        allowed_edit_paths = sorted(
            path
            for path in set(public_files).union(reference_files)
            if not path.startswith("tests/") and path != "task.md"
        )
        manifest_tasks.append({
            "task_id": task.task_id,
            "cohort": task.cohort,
            "stratum": task.stratum,
            "kind": task.kind,
            "workspace_path": f"tasks/{task.task_id}",
            "hidden_tests_path": f"hidden-tests/{task.task_id}",
            "reference_path": f"references/{task.task_id}",
            "allowed_edit_paths": allowed_edit_paths,
            "public_command": PUBLIC_COMMAND,
            "hidden_command": PUBLIC_COMMAND,
            "workspace_tree_sha256": tree_digest(public_root),
            "hidden_tests_tree_sha256": tree_digest(hidden_root),
            "reference_tree_sha256": tree_digest(reference_root),
        })

    manifest = cast(dict[str, object], {
        "schema_version": 2,
        "corpus_id": "effect-corpus-v9-cleanup",
        "profile": "cleanup",
        "generated_by": "scripts/materialize_effect_corpus_v9.py --profile cleanup",
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
        "cleanup_contract": {
            "kinds": ["replace", "duplicate", "retain", "docs"],
            "hidden_checks": ["current_behavior", "retirement_hygiene"],
            "multi_file_surfaces": True,
            "deletion_is_scoped_and_hash_safe": True,
            "reference_implementation_is_not_available_to_agent": True,
        },
        "tasks": manifest_tasks,
    })
    corpus.mkdir(parents=True, exist_ok=True)
    _ = (corpus / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


@dataclass(frozen=True)
class CleanupV10Spec:
    task_id: str
    cohort: str
    stratum: str
    kind: str
    description: str


def cleanup_v10_tasks() -> list[CleanupV10Spec]:
    """Create adversarial multi-file retirement cases without changing frozen V9 inputs."""
    strata = ("single-module",) * 6 + ("cross-module",) * 8 + ("integration",) * 6
    kinds = ("split_owner", "dynamic_retain", "semantic_duplicate", "release_drift")
    descriptions = {
        "split_owner": "Move normalization to its canonical owner and retire the replaced module and every stale contract surface.",
        "dynamic_retain": "Update a canonical policy while preserving the adapter selected by a runtime registry.",
        "semantic_duplicate": "Reuse the canonical normalizer and remove the differently named semantic duplicate.",
        "release_drift": "Keep the current implementation while synchronizing release, version, and recovery documentation.",
    }
    return [
        CleanupV10Spec(
            task_id=f"cleanup_v10_{('decision_retention' if index < 20 else 'repair')}_{kinds[index % len(kinds)]}_{index + 1:02d}",
            cohort="decision-retention" if index < 20 else "repair",
            stratum=strata[index % len(strata)],
            kind=kinds[index % len(kinds)],
            description=descriptions[kinds[index % len(kinds)]] + "\n",
        )
        for index in range(40)
    ]


def cleanup_v10_source(task: CleanupV10Spec, *, fixed: bool) -> dict[str, str]:
    """Render one complete source/documentation surface for a V10 retirement task."""
    marker_old = f"legacy_contract_{task.task_id}"
    marker_new = f"canonical_contract_{task.task_id}"
    buggy_logic = "value.lower()" if task.cohort == "repair" else "value.strip().lower()"
    fixed_logic = "value.strip().lower()"
    common = {
        "task.md": task.description,
        "tests/test_public.py": (
            "import unittest\n\n"
            "from policy import evaluate\n\n"
            "class PublicContract(unittest.TestCase):\n"
            "    def test_visible_behavior(self):\n"
            "        self.assertEqual(evaluate('User'), 'user')\n"
        ),
        "README.md": f"# {marker_new if fixed else marker_old}\nCurrent owners use the canonical normalizer.\n",
        f"docs/{task.task_id}.md": f"{marker_new if fixed else marker_old}: policy contract.\n",
    }
    if task.kind == "split_owner":
        if fixed:
            return common | {
                "policy.py": f'"""{marker_new}."""\n\ndef canonical_normalize(value):\n    return {fixed_logic}\n\ndef evaluate(value):\n    return canonical_normalize(value)\n',
                "release-notes.md": f"{marker_new}: legacy module retired.\n",
                "package-metadata.json": json.dumps({"contract": marker_new}, sort_keys=True) + "\n",
            }
        return common | {
            "policy.py": f'"""{marker_old}."""\n\nfrom legacy.{task.task_id} import legacy_normalize\n\ndef evaluate(value):\n    return legacy_normalize(value)\n',
            f"legacy/{task.task_id}.py": f"def legacy_normalize(value):\n    return {buggy_logic}\n",
            "release-notes.md": f"{marker_old}: legacy module remains supported.\n",
            "package-metadata.json": json.dumps({"contract": marker_old}, sort_keys=True) + "\n",
        }
    if task.kind == "dynamic_retain":
        adapter = f"plugins.{task.task_id}_adapter"
        return common | {
            "policy.py": f'"""{marker_new if fixed else marker_old}."""\n\ndef canonical_normalize(value):\n    return {fixed_logic}\n\ndef evaluate(value):\n    return canonical_normalize(value)\n',
            f"plugins/{task.task_id}_adapter.py": f"def normalize(value):\n    return {fixed_logic}\n",
            f"runtime/{task.task_id}.json": json.dumps({"adapter": adapter}, sort_keys=True) + "\n",
            "runbook.md": f"{marker_new if fixed else marker_old}: runtime adapter stays registered.\n",
        }
    if task.kind == "semantic_duplicate":
        helper = f"helpers/{task.task_id}_alias.py"
        if fixed:
            return common | {
                "policy.py": f'"""{marker_new}."""\n\ndef canonical_normalize(value):\n    return {fixed_logic}\n\ndef evaluate(value):\n    return canonical_normalize(value)\n',
                "release-notes.md": f"{marker_new}: duplicate helper removed.\n",
            }
        return common | {
            "policy.py": f'"""{marker_old}."""\n\nfrom helpers.{task.task_id}_alias import normalize_alias\n\ndef canonical_normalize(value):\n    return {fixed_logic}\n\ndef evaluate(value):\n    return normalize_alias(value)\n',
            helper: f"def normalize_alias(value):\n    return {buggy_logic}\n",
            "release-notes.md": f"{marker_old}: alternate helper remains canonical.\n",
        }
    return common | {
        "policy.py": f'"""{marker_new if fixed else marker_old}."""\n\ndef canonical_normalize(value):\n    return {fixed_logic}\n\ndef evaluate(value):\n    # {marker_new if fixed else marker_old}\n    return canonical_normalize(value)\n',
        "CHANGELOG.md": f"{marker_new if fixed else marker_old}: request normalization behavior.\n",
        "VERSION.md": f"{marker_new if fixed else marker_old}: supported contract description.\n",
        "runbook.md": f"{marker_new if fixed else marker_old}: diagnose and recover this path.\n",
    }


def cleanup_v10_hidden_test(task: CleanupV10Spec) -> str:
    marker_old = f"legacy_contract_{task.task_id}"
    files = {
        "split_owner": ["policy.py", "README.md", f"docs/{task.task_id}.md", "release-notes.md", "package-metadata.json"],
        "dynamic_retain": ["policy.py", "README.md", f"docs/{task.task_id}.md", "runbook.md"],
        "semantic_duplicate": ["policy.py", "README.md", f"docs/{task.task_id}.md", "release-notes.md"],
        "release_drift": ["policy.py", "README.md", f"docs/{task.task_id}.md", "CHANGELOG.md", "VERSION.md", "runbook.md"],
    }[task.kind]
    hygiene = "\n".join(
        f"        self.assertNotIn({marker_old!r}, Path({relative!r}).read_text(encoding='utf-8'))"
        for relative in files
    )
    special = {
        "split_owner": (
            f"        self.assertFalse(Path('legacy/{task.task_id}.py').exists())\n"
            "        self.assertNotIn('legacy_normalize', Path('policy.py').read_text(encoding='utf-8'))"
        ),
        "dynamic_retain": (
            "        registry = json.loads(Path('runtime/" + task.task_id + ".json').read_text(encoding='utf-8'))\n"
            f"        self.assertEqual(registry['adapter'], 'plugins.{task.task_id}_adapter')\n"
            f"        self.assertTrue(Path('plugins/{task.task_id}_adapter.py').is_file())\n"
            "        adapter = importlib.import_module(registry['adapter'])\n"
            "        self.assertEqual(adapter.normalize(' User '), 'user')"
        ),
        "semantic_duplicate": (
            f"        self.assertFalse(Path('helpers/{task.task_id}_alias.py').exists())\n"
            "        self.assertNotIn('normalize_alias', Path('policy.py').read_text(encoding='utf-8'))"
        ),
        "release_drift": "        self.assertNotIn('legacy_contract', Path('policy.py').read_text(encoding='utf-8'))",
    }[task.kind]
    return (
        "import importlib\nimport json\nfrom pathlib import Path\nimport unittest\n\n"
        "from policy import evaluate\n\n"
        "class HiddenContract(unittest.TestCase):\n"
        "    def test_hidden_behavior(self):\n"
        "        self.assertEqual(evaluate(' User '), 'user')\n\n"
        "    def test_complete_retirement_or_retention(self):\n"
        f"{hygiene}\n"
        f"{special}\n"
    )


def materialize_cleanup_v10(corpus: Path) -> dict[str, object]:
    """Materialize deeper cleanup traps with dynamic loading and release-knowledge drift."""
    tasks = cleanup_v10_tasks()
    if corpus.exists():
        raise FileExistsError(f"refusing to overwrite existing corpus: {corpus}")
    manifest_tasks: list[dict[str, object]] = []
    for task in tasks:
        public_root = corpus / "tasks" / task.task_id
        hidden_root = corpus / "hidden-tests" / task.task_id
        reference_root = corpus / "references" / task.task_id
        public_files = cleanup_v10_source(task, fixed=False)
        reference_files = cleanup_v10_source(task, fixed=True)
        hidden_test = cleanup_v10_hidden_test(task)
        write_tree(public_root, public_files)
        write_tree(hidden_root, {"tests/test_hidden.py": hidden_test})
        write_tree(reference_root, reference_files | {"tests/test_hidden.py": hidden_test})
        allowed = sorted(relative for relative in set(public_files).union(reference_files) if relative not in {"task.md", "tests/test_public.py"})
        manifest_tasks.append({
            "task_id": task.task_id,
            "cohort": task.cohort,
            "stratum": task.stratum,
            "kind": task.kind,
            "workspace_path": f"tasks/{task.task_id}",
            "hidden_tests_path": f"hidden-tests/{task.task_id}",
            "reference_path": f"references/{task.task_id}",
            "allowed_edit_paths": allowed,
            "public_command": PUBLIC_COMMAND,
            "hidden_command": PUBLIC_COMMAND,
            "workspace_tree_sha256": tree_digest(public_root),
            "hidden_tests_tree_sha256": tree_digest(hidden_root),
            "reference_tree_sha256": tree_digest(reference_root),
        })
    manifest = cast(dict[str, object], {
        "schema_version": 2,
        "corpus_id": "effect-corpus-v10-cleanup",
        "profile": "cleanup-v10",
        "generated_by": "scripts/materialize_effect_corpus_v9.py --profile cleanup-v10",
        "task_count": len(tasks),
        "cohorts": EXPECTED_COHORTS,
        "strata_per_cohort": EXPECTED_STRATA,
        "conditions": CONDITIONS,
        "cleanup_contract": {
            "kinds": ["split_owner", "dynamic_retain", "semantic_duplicate", "release_drift"],
            "hidden_checks": ["current_behavior", "cross_file_retirement", "dynamic_runtime_retention", "release_knowledge_sync"],
            "multi_file_surfaces": True,
            "reference_implementation_is_not_available_to_agent": True,
        },
        "tasks": manifest_tasks,
    })
    corpus.mkdir(parents=True, exist_ok=True)
    _ = (corpus / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    _ = parser.add_argument("--corpus", type=Path, required=True)
    _ = parser.add_argument("--profile", choices=("v9", "cleanup", "cleanup-v10"), default="v9")
    arguments = cast(dict[str, object], vars(parser.parse_args()))
    corpus = cast(Path, arguments["corpus"])
    if arguments["profile"] == "cleanup":
        _ = materialize_cleanup(corpus)
    elif arguments["profile"] == "cleanup-v10":
        _ = materialize_cleanup_v10(corpus)
    else:
        _ = materialize(corpus)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
