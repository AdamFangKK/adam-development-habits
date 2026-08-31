#!/usr/bin/env python3
"""Materialize a fresh cleanup corpus for protocol-isolated native-agent trials."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from materialize_effect_corpus_v9 import tree_digest, write_tree


PUBLIC_COMMAND = ["python3", "-m", "unittest", "discover", "-s", "tests"]
CONDITIONS = ["no_skill", "old_skill", "new_skill"]
CURRENT_CONTRACT = "policy.canonical_normalize"


@dataclass(frozen=True)
class TaskSpec:
    task_id: str
    cohort: str
    stratum: str


TASKS = (
    TaskSpec("native_v2_cleanup_tenant_casefold", "decision-retention", "single-module"),
    TaskSpec("native_v2_cleanup_header_trim", "decision-retention", "single-module"),
    TaskSpec("native_v2_cleanup_route_slug", "decision-retention", "cross-module"),
    TaskSpec("native_v2_cleanup_account_label", "decision-retention", "cross-module"),
    TaskSpec("native_v2_cleanup_audit_key", "decision-retention", "integration"),
    TaskSpec("native_v2_cleanup_request_slug", "repair", "single-module"),
    TaskSpec("native_v2_cleanup_team_alias", "repair", "single-module"),
    TaskSpec("native_v2_cleanup_tenant_route", "repair", "cross-module"),
    TaskSpec("native_v2_cleanup_sync_label", "repair", "cross-module"),
    TaskSpec("native_v2_cleanup_release_key", "repair", "integration"),
)


def old_marker(task: TaskSpec) -> str:
    return f"legacy_contract_{task.task_id}"


def policy_source(task: TaskSpec, *, reference: bool) -> str:
    marker = CURRENT_CONTRACT if reference else old_marker(task)
    # Decision-retention fixtures already have correct runtime behavior. Their
    # trap is the still-present obsolete helper and old explanatory contract.
    # Repair fixtures require both the behavior repair and the retirement pass.
    needs_legacy_runtime = not reference and task.cohort == "repair"
    legacy_import = f"from legacy.{task.task_id} import legacy_normalize\n\n" if needs_legacy_runtime else ""
    evaluation = "legacy_normalize(value)" if needs_legacy_runtime else "canonical_normalize(value)"
    return f'''"""{marker}: policy normalization contract."""

{legacy_import}def canonical_normalize(value):
    return "-".join(value.strip().casefold().split())


def evaluate(value):
    return {evaluation}
'''


def task_description() -> str:
    return """# Canonical normalizer update

Move normalization responsibility to `policy.canonical_normalize` for the next
canonical pipeline. Its required semantics are: trim surrounding whitespace,
casefold, and collapse every internal whitespace run to one ASCII `-`. For
example, `" User Name "` must become `"user-name"`; this intentionally
replaces the legacy behavior. Route every visible consumer through that
canonical owner. Update or remove all old contract descriptions and retired
implementation paths. Do not add dependencies, do not modify tests, and work
only in this workspace.

Run the supplied public tests before finishing.
"""


def public_test(task: TaskSpec) -> str:
    if task.stratum == "single-module":
        import_line = "from policy import evaluate as visible_consumer"
    elif task.stratum == "cross-module":
        import_line = f"from consumers.{task.task_id}_consumer import request_value as visible_consumer"
    else:
        import_line = "from runtime_loader import runtime_value as visible_consumer"
    return f"""import unittest

{import_line}


class PublicContract(unittest.TestCase):
    def test_normalization(self):
        self.assertEqual(visible_consumer(" User Name "), "user-name")
"""


def explanatory_source(task: TaskSpec, *, reference: bool) -> dict[str, str]:
    contract = CURRENT_CONTRACT if reference else old_marker(task)
    statement = "policy owns the canonical normalizer" if reference else "legacy helper remains canonical"
    return {
        "README.md": f"{contract}: {statement}.\n",
        f"docs/{task.task_id}.md": f"{contract}: current normalization owner.\n",
        "runbook.md": f"{contract}: recovery uses the documented normalization owner.\n",
        "package-metadata.json": json.dumps({"normalization_contract": contract}, sort_keys=True) + "\n",
    }


def cross_module_source(task: TaskSpec) -> dict[str, str]:
    return {
        f"consumers/{task.task_id}_consumer.py": (
            "from policy import evaluate\n\n"
            "def request_value(value):\n"
            "    return evaluate(value)\n"
        )
    }


def integration_source(task: TaskSpec, *, reference: bool) -> dict[str, str]:
    adapter_module = f"plugins.{task.task_id}_adapter"
    needs_legacy_runtime = not reference and task.cohort == "repair"
    adapter_import = (
        f"from legacy.{task.task_id} import legacy_normalize"
        if needs_legacy_runtime
        else "from policy import canonical_normalize"
    )
    adapter_call = "legacy_normalize(value)" if needs_legacy_runtime else "canonical_normalize(value)"
    return {
        f"plugins/{task.task_id}_adapter.py": (
            f"{adapter_import}\n\n"
            "def normalize(value):\n"
            f"    return {adapter_call}\n"
        ),
        f"runtime/{task.task_id}.json": json.dumps({"adapter": adapter_module}, sort_keys=True) + "\n",
        "runtime_loader.py": (
            "import importlib\n"
            "import json\n"
            "from pathlib import Path\n\n"
            "def runtime_value(value):\n"
            f"    registry = json.loads(Path('runtime/{task.task_id}.json').read_text(encoding='utf-8'))\n"
            "    return importlib.import_module(registry['adapter']).normalize(value)\n"
        ),
    }


def source_files(task: TaskSpec, *, reference: bool) -> dict[str, str]:
    source = {
        "policy.py": policy_source(task, reference=reference),
        "task.md": task_description(),
        "tests/test_public.py": public_test(task),
    }
    source.update(explanatory_source(task, reference=reference))
    if not reference:
        source[f"legacy/{task.task_id}.py"] = "def legacy_normalize(value):\n    return value.strip().casefold()\n"
    if task.stratum == "cross-module":
        source.update(cross_module_source(task))
    elif task.stratum == "integration":
        source.update(integration_source(task, reference=reference))
    return source


def hidden_test(task: TaskSpec) -> str:
    marker = old_marker(task)
    prose_checks = "\n".join(
        f"        self.assertNotIn({marker!r}, Path({path!r}).read_text(encoding='utf-8'))\n"
        f"        self.assertIn({CURRENT_CONTRACT!r}, Path({path!r}).read_text(encoding='utf-8'))"
        for path in ("README.md", f"docs/{task.task_id}.md", "runbook.md")
    )
    import_line = "from policy import evaluate as visible_consumer"
    topology_imports = ""
    topology_checks = ""
    if task.stratum == "cross-module":
        import_line = f"from consumers.{task.task_id}_consumer import request_value as visible_consumer"
        topology_imports = f"from consumers import {task.task_id}_consumer as consumer_module"
        topology_checks = (
            "\n        with mock.patch.object(consumer_module, 'evaluate', return_value='delegated-owner') as owner:\n"
            "            self.assertEqual(consumer_module.request_value(' ignored '), 'delegated-owner')\n"
            "            owner.assert_called_once_with(' ignored ')"
        )
    elif task.stratum == "integration":
        adapter_module = f"plugins.{task.task_id}_adapter"
        adapter_path = f"plugins/{task.task_id}_adapter.py"
        import_line = "from runtime_loader import runtime_value as visible_consumer"
        topology_imports = "import importlib"
        topology_checks = (
            f"\n        registry = json.loads(Path('runtime/{task.task_id}.json').read_text(encoding='utf-8'))\n"
            f"        self.assertEqual(registry['adapter'], {adapter_module!r})\n"
            f"        self.assertTrue(Path({adapter_path!r}).is_file())\n"
            f"        adapter = importlib.import_module({adapter_module!r})\n"
            "        with mock.patch.object(adapter, 'canonical_normalize', return_value='delegated-owner') as owner:\n"
            "            self.assertEqual(adapter.normalize(' ignored '), 'delegated-owner')\n"
            "            owner.assert_called_once_with(' ignored ')"
        )
    return f"""import json
from pathlib import Path
import unittest
from unittest import mock

{topology_imports}

{import_line}


class HiddenCleanupContract(unittest.TestCase):
    def test_behavior_owner_and_current_documentation(self):
        self.assertEqual(visible_consumer(" User Name "), "user-name")
        policy = Path("policy.py").read_text(encoding="utf-8")
        self.assertIn("def canonical_normalize", policy)
        self.assertIn({CURRENT_CONTRACT!r}, policy)
        self.assertNotIn({marker!r}, policy)
        self.assertNotIn("legacy_normalize", policy)
        self.assertFalse(Path("legacy/{task.task_id}.py").exists())
{prose_checks}
        metadata = json.loads(Path("package-metadata.json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["normalization_contract"], {CURRENT_CONTRACT!r})
{topology_checks}
"""


def materialize_native_cleanup_effect_v2(corpus: Path) -> dict[str, object]:
    """Create public, hidden, and reference trees without overwriting prior input."""
    if corpus.exists():
        raise FileExistsError(f"refusing to overwrite existing corpus: {corpus}")
    records: list[dict[str, object]] = []
    for task in TASKS:
        task_root = corpus / "tasks" / task.task_id
        hidden_root = corpus / "hidden-tests" / task.task_id
        reference_root = corpus / "references" / task.task_id
        public_files = source_files(task, reference=False)
        reference_files = source_files(task, reference=True)
        hidden_files = {"tests/test_hidden.py": hidden_test(task)}
        write_tree(task_root, public_files)
        write_tree(hidden_root, hidden_files)
        write_tree(reference_root, reference_files | hidden_files)
        records.append(
            {
                "task_id": task.task_id,
                "cohort": task.cohort,
                "stratum": task.stratum,
                "workspace_path": f"tasks/{task.task_id}",
                "hidden_tests_path": f"hidden-tests/{task.task_id}",
                "reference_path": f"references/{task.task_id}",
                "allowed_edit_paths": sorted(
                    path for path in set(public_files).union(reference_files) if path not in {"task.md", "tests/test_public.py"}
                ),
                "public_command": PUBLIC_COMMAND,
                "hidden_command": PUBLIC_COMMAND,
                "workspace_tree_sha256": tree_digest(task_root),
                "hidden_tests_tree_sha256": tree_digest(hidden_root),
                "reference_tree_sha256": tree_digest(reference_root),
            }
        )
    manifest: dict[str, object] = {
        "schema_version": 1,
        "corpus_id": "native-cleanup-effect-v2",
        "profile": "native-cleanup-effect-v2",
        "task_count": len(TASKS),
        "conditions": CONDITIONS,
        "task_contract": {
            "agent_visible": ["tasks/<task-id> only"],
            "hidden_after_agent_exit": True,
            "reference_never_available_to_agent": True,
            "checks": [
                "canonical_owner",
                "positive_documentation_and_metadata_sync",
                "cross_module_consumer",
                "exact_dynamic_consumer_delegation",
                "behavior",
            ],
        },
        "tasks": records,
    }
    write_tree(corpus, {"manifest.json": json.dumps(manifest, indent=2, sort_keys=True) + "\n"})
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    _ = parser.add_argument("--corpus", required=True, type=Path)
    arguments = parser.parse_args()
    print(json.dumps(materialize_native_cleanup_effect_v2(arguments.corpus), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
