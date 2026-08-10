from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "SKILL.md"
README = ROOT / "README.md"
AGENT_METADATA = ROOT / "agents" / "openai.yaml"


class SkillContractTests(unittest.TestCase):
    skill: str = ""
    readme: str = ""
    metadata: str = ""

    def setUp(self) -> None:  # pyright: ignore[reportImplicitOverride]
        self.skill = SKILL.read_text(encoding="utf-8")
        self.readme = README.read_text(encoding="utf-8")
        self.metadata = AGENT_METADATA.read_text(encoding="utf-8")

    def test_quality_disciplines_are_normative_sections(self) -> None:
        for heading in (
            "## Causal Execution Discipline",
            "## Measuring Skill Effect",
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
        self.assertIn("If a counterfactual is only proposed or its result is unrun, the causal conclusion is `unknown`", self.skill)
        self.assertIn("End every Causal Full response with one exact line", self.skill)
        self.assertIn("Causal conclusion: unknown", self.skill)
        self.assertIn("A read-only diagnosis remains unknown even if it runs an in-memory probe", self.skill)
        self.assertIn("call the owner only a candidate", self.skill)
        self.assertIn("a retryable **pre-acceptance** rejection restores the state", self.skill)

    def test_front_loaded_causal_repair_card_preserves_the_owner_first_sequence(self) -> None:
        card = self.skill.index("## Causal Repair Card")
        detailed_policy = self.skill.index("## Causal Execution Discipline")
        self.assertLess(card, detailed_policy)
        for requirement in (
            "symptom** from the violated **invariant",
            "trigger -> decision or state owner -> side effect -> symptom",
            "one primary hypothesis and one plausible alternative",
            "lowest-risk discriminating probe",
            "responsible decision or state owner, not the nearest downstream consumer",
            "Causal conclusion: unknown",
        ):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, self.skill[card:detailed_policy])

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

    def test_explicit_budgets_require_visible_scale_and_boundary_probe(self) -> None:
        self.assertIn("treat a passing public example as necessary but insufficient", self.skill)
        self.assertIn("estimate the changed path's worst-case complexity", self.skill)
        self.assertIn("run a deterministic boundary probe", self.skill)
        self.assertIn("hidden scale remains a residual risk", self.skill)

    def test_budget_aware_repair_gate_blocks_semantic_only_repairs(self) -> None:
        for requirement in (
            "## Budget-Aware Repair Gate",
            "Shape: <caller-controlled dimensions",
            "Worst case: <time, space, and failure mode",
            "Bound: <the required timeout/memory/call budget",
            "Do not preserve recursion, repeated slicing",
            "Prefer a complexity bound expressed in input size",
            "budget unverified",
            "Separate semantic repair from performance repair",
            "multiple valid outputs",
        ):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, self.skill)

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

    def test_effect_claims_require_preregistration_and_scoped_evidence(self) -> None:
        self.assertIn("A finite experiment cannot prove an overall model capability", self.skill)
        self.assertIn("Cluster repeated runs by task", self.skill)
        self.assertIn("completed analysis reports `improved`", self.skill)
        self.assertIn("Skill 效果的统计检验", self.readme)

    def test_compound_level_two_gate_preserves_independent_delivery_decisions(self) -> None:
        self.assertIn("three or more triggered delivery rows", self.skill)
        self.assertIn("mitigate now`, `stage separately`, or `block pending evidence`", self.skill)
        self.assertIn("deploy with the flag disabled", self.skill)
        self.assertIn("reject force-merge or bypass", self.skill)
        self.assertIn("backfill metric and threshold", self.skill)
        self.assertIn("non-secret fixture plus a clean worktree", self.skill)
        self.assertIn("explicitly reject force-merge of red CI", self.skill)
        self.assertIn("standalone `Operational knowledge:` and `Reproducibility:` lines", self.skill)
        self.assertIn("复合门槛", self.readme)


if __name__ == "__main__":
    _ = unittest.main()
