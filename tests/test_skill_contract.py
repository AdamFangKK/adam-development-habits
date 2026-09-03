from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "SKILL.md"
README = ROOT / "README.md"
AGENT_METADATA = ROOT / "agents" / "openai.yaml"
SECURE_CODE_PATHS = ROOT / "references" / "secure-code-paths.md"


class SkillContractTests(unittest.TestCase):
    skill: str = ""
    readme: str = ""
    metadata: str = ""
    secure_code_paths: str = ""

    def setUp(self) -> None:  # pyright: ignore[reportImplicitOverride]
        self.skill = SKILL.read_text(encoding="utf-8")
        self.readme = README.read_text(encoding="utf-8")
        self.metadata = AGENT_METADATA.read_text(encoding="utf-8")
        self.secure_code_paths = SECURE_CODE_PATHS.read_text(encoding="utf-8")

    def test_quality_disciplines_are_normative_sections(self) -> None:
        for heading in (
            "## Causal Execution Discipline",
            "## Measuring Skill Effect",
            "## Maintainable Boundaries and Atomic Design",
            "## Failure Semantics and Data Ownership",
            "## Contract Evolution and Test Quality",
            "## Operational Readiness, Performance, and Security",
            "## Secure Code Path Gate",
            "## Delivery Lifecycle and Repository Hygiene",
            "## Compound Level 2 Gate",
            "## Evidence-Based AI Collaboration",
            "## Explainable Implementation and Chinese Maintenance Notes",
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

    def test_truthful_execution_protocol_blocks_silent_completion_and_context_drift(self) -> None:
        for requirement in (
            "## Truthful Execution and Context Control",
            "`planned`",
            "`executed`",
            "`verified`",
            "`blocked`",
            "Never claim a file was changed",
            "compact task contract",
            "bounded repair loop",
            "three consecutive attempts",
            "Do not hide a failing check",
            "model capability and tool authority as boundaries",
        ):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, self.skill)

    def test_evidence_first_repair_gate_is_mandatory_and_owner_first(self) -> None:
        gate = self.skill[self.skill.index("## Evidence-First Repair Gate") : self.skill.index("## Causal Repair Card")]
        for requirement in (
            "For every Level 1 or Level 2 bug fix",
            "before the first behavioral edit",
            "observe",
            "separate symptom and invariant",
            "map the full request/state path",
            "identify observable nodes and blind spots",
            "record primary and alternative hypotheses",
            "run a discriminating probe",
            "locate the earliest responsible owner",
            "perform a minimal counterfactual intervention",
            "regression test",
            "deployment/runtime verification",
            "record residual risk",
            "Level 0 documentation work",
            "any ambiguity, prior failed attempt",
        ):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, gate)

    def test_evidence_first_gate_blocks_blind_repair_and_attempt_cycling(self) -> None:
        gate = self.skill[self.skill.index("## Evidence-First Repair Gate") : self.skill.index("## Causal Repair Card")]
        for requirement in (
            "observed`, `partially observed`, or `blind",
            "first reuse or add the smallest redacted, low-cardinality probe",
            "or explicitly leave the behavioral conclusion `unknown`",
            "failed-attempt ledger",
            "actual result, failure category",
            "wrong-owner-or-symptom-patch",
            "stale-runtime-or-configuration",
            "Do not repeat a failed category without a new discriminating observation",
            "holding adjacent inputs, configuration, dependency versions, and timing assumptions fixed",
            "proposed`, `unrun`, `in-memory-only`",
            "Stop and do not claim completion",
            "Stop condition",
            "No production action is authorized by this gate",
        ):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, gate)

    def test_final_report_shape_includes_explainability(self) -> None:
        report = self.skill[self.skill.index("## Final Report Format") :]
        self.assertIn("Explainability: <comments added/updated or not applicable; review result>", report)
        self.assertIn("单列 `Explainability:`", self.readme)

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

    def test_machine_evidence_v2_binds_decisions_verification_and_review(self) -> None:
        for requirement in (
            "schema_version: 2",
            "every passed verification to reference a hash-verified `command_output` or `test_output`",
            "exit code, UTC execution timestamp, and repository revision",
            "reviewer other than the implementer",
            "reference a hash-verified `review_report`",
            "Schema version 1 is read-only compatibility",
            "cannot satisfy the changed-evidence gate",
            "full lowercase `git_commit`",
            "A hash link proves artifact identity, not that its summary is true",
            "--require-level-two-for-high-risk",
        ):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, self.skill)

        self.assertIn("schema_version: 2", self.readme)
        self.assertIn("历史工件若引用旧版本文件", self.readme)

    def test_safeguard_matrix_covers_quality_and_operational_boundaries(self) -> None:
        for situation in (
            "| Mutable business or personal data |",
            "| API, event, shared-library, or configuration boundary |",
            "| Code path from untrusted input to a database, command, template, file, URL fetch, parser, deserializer, or security decision |",
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

    def test_secure_code_path_gate_requires_sink_specific_evidence(self) -> None:
        for requirement in (
            "source -> validation/normalization -> authorization or policy -> sink",
            "framework or platform's safe mechanism",
            "validation at an earlier layer never proves a later sink is safe",
            "Minimal synthetic malicious inputs are permitted in local tests and fixtures when needed",
            "never echo those inputs, real secrets, personal data, or production payloads",
            "A scan alert is a lead",
            "confirm reachability, applicable controls, and impact",
            "Secure code path: not applicable",
        ):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, self.skill)

        for heading in (
            "## Injection and Output Contexts",
            "## Authorization and Resource Ownership",
            "## Files, URLs, Parsing, and Resource Abuse",
            "## Security Finding Verification",
        ):
            with self.subTest(heading=heading):
                self.assertIn(heading, self.secure_code_paths)

        self.assertIn("source -> control -> sink", self.readme)
        self.assertEqual(self.readme.count("| 安全代码路径 |"), 1)
        self.assertIn("source -> control -> sink", self.metadata)
        self.assertIn("Minimal synthetic malicious inputs are permitted in local tests and fixtures when needed", self.secure_code_paths)
        self.assertIn("Do not echo test inputs into logs, reports, snapshots, or externally shared artifacts.", self.secure_code_paths)

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
        self.assertIn("stale paths, comments, docs, and metadata", self.metadata)
        self.assertIn("废弃说明残留", self.readme)
        self.assertIn("stale explanatory surfaces", self.skill)
        self.assertIn("证据优先修复门禁", self.readme)
        self.assertIn("failed-attempt ledger", self.metadata)
        self.assertIn("deployment/runtime verification", self.metadata)

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

    def test_explainable_implementation_requires_maintainer_focused_chinese_notes(self) -> None:
        for requirement in (
            "Explain behavior first through focused module boundaries",
            "concise Chinese comments",
            "why**, constraint, ownership rule, or failure semantics",
            "non-obvious invariant, state transition, causal-owner repair",
            "not a mechanical translation",
            "Do not add line-by-line narration",
            "Explainability: <comments added/updated or not applicable; review result>",
        ):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, self.skill)
        self.assertIn("### 可解释实现与中文维护注释", self.readme)
        self.assertIn("中文注释只解释代码本身无法可靠表达的“为什么”", self.readme)

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

    def test_compound_level_two_minimum_checklist_survives_concise_responses(self) -> None:
        checklist = self.skill[self.skill.index("For a concise compound response") : self.skill.index("## Evidence-Based AI Collaboration")]
        for requirement in (
            "Change level: 2",
            "Causal status:",
            "Remote write: durable `pending`",
            "Migration: `Expand-Migrate-Contract`",
            "backfill stop condition with a concrete metric and threshold",
            "replication lag, queue age, or error rate",
            "feature flag disabled by default",
            "disable the flag first before code rollback",
            "required CI must be green",
            "do not force-merge red CI",
            "exclude unrelated dirty worktree changes",
            "Secrets: rotate and redact",
            "Supply chain:",
            "Operational knowledge: ADR/runbook",
            "Reproducibility: non-secret fixture",
            "existing repository tools",
            "Authority: no production action",
            "Verification: exact command and observed result",
            "not applicable",
        ):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, checklist)
        self.assertIn("最小清单", self.readme)


if __name__ == "__main__":
    _ = unittest.main()
