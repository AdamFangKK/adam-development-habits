from __future__ import annotations

import json
import unittest
from pathlib import Path
from typing import cast


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "SKILL.md"
README = ROOT / "README.md"
METADATA = ROOT / "agents" / "openai.yaml"
CORPUS = ROOT / "examples" / "retirement-cleanup-traps.json"


class RetirementCleanupContractTests(unittest.TestCase):
    skill: str = ""
    readme: str = ""
    metadata: str = ""
    corpus: dict[str, object] = {}
    policy: str = ""

    def setUp(self) -> None:  # pyright: ignore[reportImplicitOverride]
        self.skill = SKILL.read_text(encoding="utf-8")
        self.readme = README.read_text(encoding="utf-8")
        self.metadata = METADATA.read_text(encoding="utf-8")
        self.corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
        start = self.skill.index("## Automatic Retirement and Drift Cleanup")
        end = self.skill.index("When Causal Execution Discipline is active", start)
        self.policy = self.skill[start:end]

    def test_policy_is_implicit_but_risk_scaled(self) -> None:
        self.assertIn("implicit even when the user does not request it explicitly", self.skill)
        self.assertIn("Level 0 never triggers a full sweep", self.policy)
        self.assertIn("Level 1", self.policy)
        self.assertIn("Level 2", self.policy)
        self.assertIn("Search/import or call-graph output", self.policy)
        self.assertIn("migration or rollback rehearsal", self.policy)

    def test_hybrid_trap_corpus_has_distinct_expected_decisions_and_evidence(self) -> None:
        scenarios_value = self.corpus["scenarios"]
        self.assertIsInstance(scenarios_value, list)
        scenarios = cast(list[dict[str, object]], scenarios_value)
        self.assertEqual(self.corpus["schema_version"], 1)
        self.assertEqual(len(scenarios), 6)
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
        self.assertIn("same logical change", self.policy)
        self.assertIn("Retirement sweep:", self.skill)
        self.assertIn("Documentation synchronization:", self.skill)
        self.assertIn("Cleanup audit:", self.skill)

    def test_readme_exposes_automatic_behavior_and_evidence_boundary(self) -> None:
        self.assertIn("不需要用户额外说“清理垃圾代码”", self.readme)
        self.assertIn("Level 1（轻量）", self.readme)
        self.assertIn("Level 2（完整）", self.readme)
        self.assertIn("零直接引用", self.readme)
        self.assertIn("动态、生成或外部引用时不得猜删", self.readme)
        self.assertIn("Documentation synchronization:", self.readme)
        self.assertIn("automatic retirement", self.metadata)
        self.assertIn("stale paths", self.metadata)


if __name__ == "__main__":
    _ = unittest.main()
