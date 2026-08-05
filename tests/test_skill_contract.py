from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "SKILL.md"
README = ROOT / "README.md"
AGENT_METADATA = ROOT / "agents" / "openai.yaml"


class SkillContractTests(unittest.TestCase):
    def setUp(self) -> None:  # pyright: ignore[reportImplicitOverride]
        self.skill = SKILL.read_text(encoding="utf-8")
        self.readme = README.read_text(encoding="utf-8")
        self.metadata = AGENT_METADATA.read_text(encoding="utf-8")

    def test_quality_disciplines_are_normative_sections(self) -> None:
        for heading in (
            "## Causal Execution Discipline",
            "## Maintainable Boundaries and Atomic Design",
            "## Failure Semantics and Data Ownership",
            "## Contract Evolution and Test Quality",
            "## Operational Readiness, Performance, and Security",
            "## Delivery Lifecycle and Repository Hygiene",
            "## Compound Level 2 Gate",
            "## Evidence-Based AI Collaboration",
        ):
            with self.subTest(heading=heading):
                self.assertIn(heading, self.skill)

    def test_causal_full_requires_a_counterfactual_owner_and_rejects_downstream_claims(self) -> None:
        self.assertIn("trigger -> decision or state owner -> side effect -> symptom", self.skill)
        self.assertIn("minimal counterfactual intervention", self.skill)
        self.assertIn("Do not call a downstream display", self.skill)

    def test_completion_gate_and_ledger_capture_quality_decisions(self) -> None:
        for field in (
            "Design boundary:",
            "Dependency audit:",
            "Extension decision:",
            "Data ownership:",
            "Error model:",
            "Contract evolution:",
            "Operational budget:",
            "Delivery lifecycle:",
            "Release and recovery:",
            "Data migration:",
            "Configuration and secrets:",
            "Supply chain:",
            "Operational knowledge:",
            "Reproducibility:",
        ):
            with self.subTest(field=field):
                self.assertIn(field, self.skill)

        self.assertIn("ownership, lifecycle, failure semantics, compatibility, budget, and threat boundary", self.skill)
        self.assertIn("quality_decisions", self.skill)
        self.assertIn("Quality decisions:", self.skill)
        self.assertIn("Delivery decisions:", self.skill)

    def test_safeguard_matrix_covers_quality_and_operational_boundaries(self) -> None:
        for situation in (
            "| Mutable business or personal data |",
            "| API, event, shared-library, or configuration boundary |",
            "| Critical rule, public contract, or broad input domain |",
            "| Expensive or exposed operation |",
            "| Sensitive or privileged operation |",
            "| Deployable service |",
            "| Level 1 or Level 2 Git-tracked change |",
            "| Release, feature rollout, or operational configuration |",
            "| Schema, backfill, or persistence-format migration |",
            "| Configuration, environment variable, or secret |",
            "| Added or materially changed dependency |",
        ):
            with self.subTest(situation=situation):
                self.assertIn(situation, self.skill)

    def test_delivery_matrix_covers_every_requested_practice(self) -> None:
        for practice in (
            "| Atomic Git change and PR |",
            "| Release and recovery |",
            "| Data migration |",
            "| Configuration and secrets |",
            "| Dependency and supply chain |",
            "| Documentation and operational knowledge |",
            "| Reproducible development |",
        ):
            with self.subTest(practice=practice):
                self.assertIn(practice, self.skill)

    def test_readme_and_metadata_expose_the_quality_contract(self) -> None:
        for summary in (
            "| 失败语义与数据所有权 |",
            "| 契约演进与测试质量 |",
            "| 运行就绪、性能与安全 |",
            "### 失败、数据、契约与测试",
            "### 运行、性能与安全",
            "### 交付、迁移与仓库卫生",
            "Operational budget:",
        ):
            with self.subTest(summary=summary):
                self.assertIn(summary, self.readme)

        self.assertIn("$adam-development-habits", self.metadata)
        self.assertIn("boundaries", self.metadata)

    def test_complex_package_changes_require_an_isolated_composite_forward_test(self) -> None:
        self.assertIn("changes three or more of causal diagnosis, design boundaries, data/contracts", self.skill)
        self.assertIn("explicit allowed-input boundary of the raw request and Skill", self.skill)
        self.assertIn("deliberate unsafe mutations", self.skill)
        self.assertIn("protocol-isolated", self.skill)
        self.assertIn("复合陷阱前向测试", self.readme)

    def test_compound_level_two_gate_preserves_independent_delivery_decisions(self) -> None:
        self.assertIn("three or more triggered delivery rows", self.skill)
        self.assertIn("mitigate now`, `stage separately`, or `block pending evidence`", self.skill)
        self.assertIn("deploy with the flag disabled", self.skill)
        self.assertIn("reject force-merge or bypass", self.skill)
        self.assertIn("复合门槛", self.readme)


if __name__ == "__main__":
    unittest.main()
