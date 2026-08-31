from __future__ import annotations

import json
import unittest
from pathlib import Path
from typing import cast


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "SKILL.md"
README = ROOT / "README.md"
METADATA = ROOT / "agents" / "openai.yaml"
ENFORCEMENT = ROOT / "references" / "enforcement.md"
CORPUS = ROOT / "examples" / "retirement-cleanup-traps.json"
OBSERVABILITY = ROOT / "examples" / "retirement-cleanup-observability.json"


class RetirementCleanupContractTests(unittest.TestCase):
    skill: str = ""
    readme: str = ""
    metadata: str = ""
    enforcement: str = ""
    corpus: dict[str, object] = {}
    observability: dict[str, object] = {}
    policy: str = ""

    def setUp(self) -> None:  # pyright: ignore[reportImplicitOverride]
        self.skill = SKILL.read_text(encoding="utf-8")
        self.readme = README.read_text(encoding="utf-8")
        self.metadata = METADATA.read_text(encoding="utf-8")
        self.enforcement = ENFORCEMENT.read_text(encoding="utf-8")
        self.corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
        self.observability = json.loads(OBSERVABILITY.read_text(encoding="utf-8"))
        start = self.skill.index("## Automatic Retirement and Drift Cleanup")
        end = self.skill.index("When Causal Execution Discipline is active", start)
        self.policy = self.skill[start:end]

    def test_policy_is_implicit_but_risk_scaled(self) -> None:
        self.assertIn("implicit even when the user does not request it explicitly", self.skill)
        self.assertIn("must not wait for the user to ask for cleanup explicitly", self.policy)
        self.assertIn("stale explanatory surfaces", self.policy)
        self.assertIn("Level 0 never triggers a full sweep", self.policy)
        self.assertIn("Level 1", self.policy)
        self.assertIn("Level 2", self.policy)
        self.assertIn("Search/import or call-graph output", self.policy)
        self.assertIn("migration or rollback rehearsal", self.policy)

    def test_retirement_quick_gate_front_loads_cross_surface_identifier_cleanup(self) -> None:
        quick_gate = self.skill.index("## Retirement Quick Gate")
        detailed_policy = self.skill.index("## Automatic Retirement and Drift Cleanup")
        self.assertLess(quick_gate, detailed_policy)
        for requirement in (
            "inspect every existing non-test file in the changed boundary before editing",
            "retired code identifiers, imports, exports, registry keys, flags, and paths",
            "old contract markers taken from source docstrings/comments and README/API/docs/changelog/release/version/metadata text",
            "search every existing non-test file in the changed boundary, plus every changed explanatory surface, for every recorded value",
            "Do not finish while an old marker remains merely because a public test passes",
            "A document is a lead, not a consumer",
            "named live runtime/API consumer or a verifiable external compatibility obligation",
            "classify it `unknown` and stop completion",
        ):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, self.skill[quick_gate:detailed_policy])

    def test_checkpoint_orders_reuse_sweep_description_sync_and_unknown_stop(self) -> None:
        for requirement in (
            "Before implementation",
            "reuse_existing_owner",
            "After implementation and before the final verification/commit",
            "duplicate-code or static-analysis tool",
            "normalized control flow",
            "Synchronize descriptions in the same change",
            "old behavior phrases",
            "Write a retirement inventory before deleting anything",
            "post-retirement orphan scan",
            "current source/contract as the authority",
            "A file deletion is valid only when the deleted path is listed in the change scope",
            "Stop the completion gate when evidence is unresolved",
            "Do not silently retain an unknown path",
        ):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, self.policy)

    def test_hybrid_trap_corpus_has_distinct_expected_decisions_and_evidence(self) -> None:
        scenarios_value = self.corpus["scenarios"]
        self.assertIsInstance(scenarios_value, list)
        scenarios = cast(list[dict[str, object]], scenarios_value)
        self.assertEqual(self.corpus["schema_version"], 2)
        self.assertEqual(len(scenarios), 10)
        self.assertEqual(
            {cast(str, scenario["expected"]) for scenario in scenarios},
            {"remove", "retain", "unknown", "reuse_existing_owner"},
        )
        self.assertEqual(len({cast(str, scenario["id"]) for scenario in scenarios}), len(scenarios))
        for scenario in scenarios:
            with self.subTest(scenario=cast(str, scenario["id"])):
                self.assertTrue(cast(str, scenario["trigger"]))
                self.assertTrue(cast(str, scenario["trap"]))
                self.assertGreaterEqual(len(cast(list[str], scenario["required_evidence"])), 3)

    def test_policy_defends_against_each_trap_without_equating_no_reference_with_dead(self) -> None:
        required_policy_terms = {
            "remove": "`remove`: the new owner handles the responsibility",
            "retain": "`retain`: a named consumer or compatibility obligation still exists",
            "unknown": "`unknown`: a dynamic, generated, external, or otherwise unresolved reference may exist",
            "reuse_existing_owner": "Search for an existing owner, utility, extension point, or adapter before adding another implementation",
        }
        scenarios = cast(list[dict[str, object]], self.corpus["scenarios"])
        expected_values = {cast(str, scenario["expected"]) for scenario in scenarios}
        for expected in expected_values:
            with self.subTest(expected=expected):
                self.assertIn(required_policy_terms[expected], self.policy)

        for guard in (
            "zero direct-reference result",
            "green public test alone",
            "Do not delete it or call the change complete",
            "real consumer, removal condition, observability, and coverage",
        ):
            with self.subTest(guard=guard):
                self.assertIn(guard, self.policy)

    def test_documentation_cannot_be_a_standalone_retention_consumer(self) -> None:
        for requirement in (
            "is **not a consumer by itself**",
            "cannot independently justify `retain`",
            "live runtime/API consumer or a verifiable external compatibility obligation",
            "authoritative contract, owner, and expiry",
            "stale or unverified project document is not such a commitment",
            "classify the superseded path as `remove`",
        ):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, self.policy)
        self.assertIn("本身不是消费者", self.readme)
        self.assertIn("不能单独成为保留旧实现的理由", self.readme)

    def test_all_implementation_surfaces_and_explanatory_drift_are_named(self) -> None:
        for surface in (
            "tests",
            "fixtures",
            "types",
            "exports",
            "dependencies",
            "routes",
            "jobs",
            "queues",
            "flags",
            "environment keys",
            "telemetry labels",
            "README/API docs",
            "ADRs",
            "runbooks",
            "examples",
            "comments",
            "version descriptions",
            "Skill/package metadata",
        ):
            with self.subTest(surface=surface):
                self.assertIn(surface, self.policy)
        self.assertIn("A comment or version note that describes the old decision is stale code in another form", self.policy)
        self.assertIn("generated files and convention-based loaders", self.policy)
        self.assertIn("same logical change", self.policy)
        self.assertIn("退休清单", self.readme)
        self.assertIn("跨文件孤儿扫描", self.readme)
        self.assertIn("Retirement sweep:", self.skill)
        self.assertIn("Documentation synchronization:", self.skill)
        self.assertIn("Cleanup audit:", self.skill)

    def test_instrumentation_is_risk_scaled_and_evidence_bound(self) -> None:
        for phrase in (
            "Development and runtime instrumentation",
            "Level 0",
            "Level 1",
            "Level 2",
            "owner_located",
            "retirement_classified",
            "verification_completed",
            "stable event names",
            "bounded labels",
            "never record secrets",
            "Missing telemetry from an applicable boundary is a verification gap",
            "Instrumentation: <not applicable",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.policy if phrase != "Instrumentation: <not applicable" else self.skill)

        schema = cast(dict[str, object], self.observability["event_schema"])
        required = cast(list[str], schema["required"])
        self.assertEqual(
            required,
            ["event", "change_id", "component", "outcome", "classification", "evidence_id"],
        )
        self.assertEqual(
            set(cast(list[str], schema["forbidden_values"])),
            {"secret", "raw_payload", "personal_data", "source_text", "unbounded_user_label"},
        )
        scenarios = cast(list[dict[str, object]], self.observability["scenarios"])
        level_zero = next(item for item in scenarios if item["id"] == "pure_helper_level_0")
        self.assertEqual(level_zero["instrumentation"], "not_applicable")
        level_one = next(item for item in scenarios if item["id"] == "cleanup_boundary_level_1")
        self.assertEqual(
            set(cast(list[str], level_one["required_events"])),
            {"owner_located", "retirement_classified", "verification_completed"},
        )
        multifile = next(item for item in scenarios if item["id"] == "multifile_retirement_level_1")
        self.assertEqual(
            cast(list[str], multifile["required_evidence"]),
            ["retirement inventory", "post-retirement orphan scan", "documentation synchronization"],
        )
        level_two = next(item for item in scenarios if item["id"] == "remote_lifecycle_level_2")
        self.assertEqual(
            cast(list[str], level_two["required_events"]),
            ["started", "owner_located", "implemented", "cleanup_classified", "verified", "committed"],
        )
        trap = next(item for item in scenarios if item["id"] == "redaction_and_cardinality_trap")
        self.assertEqual(cast(list[str], trap["forbid"]), cast(list[str], schema["forbidden_values"]))

    def test_readme_exposes_automatic_behavior_and_evidence_boundary(self) -> None:
        self.assertIn("不需要用户额外说“清理垃圾代码”", self.readme)
        self.assertIn("旧注释、旧 README/API 文本、旧版本说明和旧 metadata", self.readme)
        self.assertIn("Level 1（轻量）", self.readme)
        self.assertIn("Level 2（完整）", self.readme)
        self.assertIn("零直接引用", self.readme)
        self.assertIn("动态、生成或外部引用时不得猜删", self.readme)
        self.assertIn("先复用已有 owner", self.readme)
        self.assertIn("清理检查点必须在最终验证和提交前完成", self.readme)
        self.assertIn("Documentation synchronization:", self.readme)
        self.assertIn("分层埋点与开发过程数据", self.readme)
        self.assertIn("Level 0：不新增遥测", self.readme)
        self.assertIn("retirement_classified", self.readme)
        self.assertIn("automatic retirement", self.metadata)
        self.assertIn("stale paths", self.metadata)
        self.assertIn("Before implementation reuse an existing owner", self.metadata)
        for requirement in (
            "retirement checkpoint before final verification and commit",
            "reuse a fitting existing owner",
            "normalized control-flow, contract, and call-site inspection",
            "unresolved `unknown` paths stop silent completion",
            "add instrumentation at the responsible decision and failure boundaries",
            "event names stable",
            "labels bounded",
        ):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, self.enforcement)


if __name__ == "__main__":
    _ = unittest.main()
