from __future__ import annotations

import json
import subprocess
import sys
import unittest
import tempfile
import hashlib

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from plan_capability_composition import load_catalog, plan  # noqa: E402


class CapabilityCompositionTests(unittest.TestCase):
    def test_noncanonical_whitespace_cannot_bypass_fact_gates(self):
        for kwargs in ({"facts": ["level_1 "]}, {"facts": [" level_1"]},
                       {"facts": ["level_1"], "required_facts": ["owner_located "]},
                       {"facts": ["level_1"], "previous_facts": ["level_1 "]}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                plan(**kwargs)

    def test_prerequisite_status_remains_applicable_after_search_budget(self):
        result = plan(["level_1", "refactor"], max_rounds=1)
        owner = next(item for item in result["capability_status"] if item["capability"] == "owner_mapping")
        self.assertIn(owner["status"], {"deferred", "unknown"})
        self.assertNotEqual(owner["status"], "not_applicable")

    def test_catalog_rejects_surrounding_whitespace(self):
        for field in ("id", "purpose", "trigger_any", "requires_all", "produces"):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                cards = load_catalog()
                cards[0][field] = " invalid " if field in {"id", "purpose"} else [" invalid "]
                catalog = Path(directory) / "catalog.json"
                catalog.write_text(json.dumps({"schema_version": 1, "capabilities": cards}), encoding="utf-8")
                with self.assertRaises(ValueError):
                    load_catalog(catalog)

    def test_hash_bound_evidence_reuses_completion_and_invalidates_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            artifact = Path(directory) / "result.txt"
            artifact.write_text("reviewed result", encoding="utf-8")
            records = [{"capability": capability, "path": str(artifact),
                        "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
                        "revision": "revision-a", "context_facts": ["level_1"]}
                       for capability in ("risk_triage", "evidence_ledger")]
            result = plan(["level_1"], evidence_records=records, context_revision="revision-a")
            self.assertFalse(result["blocked"])
            self.assertEqual(result["selected"], [])
            self.assertEqual(set(result["satisfied"]), {"risk_triage", "evidence_ledger"})
            self.assertTrue(set(result["satisfied"]).isdisjoint(
                item["capability"] for item in result["rejected"]
            ))
            self.assertIn("risk_classified", result["verified_facts"])
            for revision, facts in (("revision-b", ["level_1"]), ("revision-a", ["level_1", "rename"])):
                result = plan(facts, evidence_records=records, context_revision=revision)
                self.assertEqual(result["satisfied"], [])
                self.assertEqual(len(result["invalidated_evidence"]), 2)
                self.assertIn("risk_triage", result["selected"])
            artifact.write_text("changed result", encoding="utf-8")
            result = plan(["level_1"], evidence_records=records, context_revision="revision-a")
            self.assertEqual(result["verified_facts"], [])
            self.assertEqual(len(result["invalidated_evidence"]), 2)

    def test_acceptance_does_not_invent_unrelated_optional_triggers(self):
        result = plan(["level_1"], required_facts=["secure_path_evidence"])
        self.assertTrue(result["blocked"])
        self.assertNotIn("security_gate", result["selected"])

    def test_raw_output_label_cannot_satisfy_acceptance(self):
        result = plan(["level_1", "secure_path_evidence"], required_facts=["secure_path_evidence"])
        self.assertTrue(result["blocked"])
        self.assertEqual(result["verified_facts"], [])

    def test_level_zero_rejects_every_catalog_risk_trigger(self):
        outputs = {fact for card in load_catalog() for fact in card["produces"]}
        triggers = {fact for card in load_catalog() for fact in card["trigger_any"]} - outputs - {"rename"}
        for trigger in triggers:
            with self.subTest(trigger=trigger), self.assertRaises(ValueError):
                plan(["level_0", trigger])

    def test_refactor_resolves_untriggered_owner_prerequisite(self):
        result = plan(["level_1", "refactor"])
        self.assertFalse(result["blocked"])
        self.assertIn("owner_mapping", result["selected"])

    def test_existing_output_labels_are_rechecked_not_false_blocked(self):
        result = plan(["level_1", "risk_classified", "evidence_recorded"])
        self.assertFalse(result["blocked"])
        self.assertIn("risk_triage", result["selected"])
        self.assertEqual(result["verified_facts"], [])

    def test_level_zero_is_noop(self):
        result = plan(["level_0", "rename", "owner_located"])
        self.assertEqual(result["selected"], [])
        self.assertFalse(result["blocked"])

    def test_malformed_inputs_are_rejected(self):
        for kwargs in ({"required_facts": [None, 123]}, {"required_facts": "abc"},
                       {"max_active": True}, {"max_rounds": 1.5}, {"beam_width": "2"},
                       {"previous_facts": [None]}, {"prior_replans": False}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                plan(["level_1"], **kwargs)
        for facts in ("level_1", ["level_0", "level_1"], ["level_0", "behavior_change"]):
            with self.subTest(facts=facts), self.assertRaises(ValueError):
                plan(facts)

    def test_catalog_cards_have_composable_contracts(self) -> None:
        cards = load_catalog()
        identifiers = {card["id"] for card in cards}
        self.assertGreaterEqual(len(cards), 10)
        self.assertEqual(len(identifiers), len(cards))
        for card in cards:
            with self.subTest(capability=card["id"]):
                self.assertTrue(card["trigger_any"])
                self.assertIn("requires_all", card)
                self.assertIn("requires_any", card)
                self.assertTrue(card["produces"])
                self.assertGreaterEqual(card["cost"], 0)
                self.assertGreaterEqual(card["risk_reduction"], 0)

    def test_replacement_plan_composes_owner_cleanup_contract_and_ledger(self) -> None:
        required = ["owner_located", "regression_evidence", "retirement_classified", "evidence_recorded"]
        result = plan(["level_1", "behavior_change", "replacement"], required_facts=required)
        selected = result["selected"]
        self.assertFalse(result["blocked"])
        for capability in ("risk_triage", "owner_mapping", "contract_tests", "retirement_cleanup", "evidence_ledger"):
            self.assertIn(capability, selected)
        for capability in ("causal_diagnosis", "security_gate", "delivery_lifecycle"):
            self.assertNotIn(capability, selected)
        owner_transition = next(item for item in result["transitions"] if item["capability"] == "owner_mapping")
        cleanup_transition = next(item for item in result["transitions"] if item["capability"] == "retirement_cleanup")
        self.assertIn("owner_located", owner_transition["produced"])
        self.assertIn("owner_located", cleanup_transition["consumed"])
        self.assertEqual(set(result["covered_required_facts"]), set(required))
        self.assertEqual(result["missing_required_facts"], [])
        self.assertLessEqual(len(result["selected"]), 6)

    def test_ambiguous_remote_write_selects_cross_boundary_capabilities(self) -> None:
        required = [
            "causal_owner_candidate",
            "node_evidence",
            "failure_modelled",
            "regression_evidence",
            "retirement_classified",
            "delivery_plan_recorded",
            "evidence_recorded",
        ]
        result = plan(
            [
                "level_2",
                "behavior_change",
                "ambiguous_failure",
                "symptom",
                "invariant",
                "remote_write",
                "external_dependency",
                "external_boundary",
                "replacement",
                "cross_boundary",
            ],
            required_facts=required,
        )
        self.assertFalse(result["blocked"])
        for capability in (
            "risk_triage",
            "owner_mapping",
            "causal_diagnosis",
            "observability",
            "failure_semantics",
            "contract_tests",
            "retirement_cleanup",
            "delivery_lifecycle",
            "evidence_ledger",
        ):
            self.assertIn(capability, result["selected"])
        self.assertIn("discriminating_probe", result["final_facts"])
        self.assertIn("unknown_outcome_policy", result["final_facts"])
        self.assertIn("documentation_synchronized", result["final_facts"])
        self.assertEqual(result["missing_required_facts"], [])
        self.assertLessEqual(len(result["selected"]), 10)
        self.assertGreaterEqual(len(result["candidate_plans"]), 1)
        self.assertLessEqual(len(result["candidate_plans"]), 3)

    def test_missing_invariant_defers_causal_capability_instead_of_guessing(self) -> None:
        result = plan(["level_1", "behavior_change", "ambiguous_failure"])
        self.assertNotIn("causal_diagnosis", result["selected"])
        rejected = {item["capability"]: item for item in result["rejected"]}
        self.assertIn("causal_diagnosis", rejected)
        self.assertEqual(rejected["causal_diagnosis"]["status"], "unknown")
        self.assertIn("invariant", rejected["causal_diagnosis"]["missing_requirements"])

    def test_partial_causal_context_does_not_satisfy_the_owner_gate(self) -> None:
        result = plan(["level_1", "behavior_change", "ambiguous_failure", "symptom"])
        self.assertNotIn("causal_diagnosis", result["selected"])
        rejected = {item["capability"]: item for item in result["rejected"]}
        self.assertEqual(rejected["causal_diagnosis"]["status"], "unknown")
        self.assertEqual(rejected["causal_diagnosis"]["missing_requirements"], ["invariant"])

    def test_active_limit_reports_deferred_mandatory_capabilities(self) -> None:
        required = ["causal_owner_candidate", "node_evidence", "failure_modelled", "delivery_plan_recorded"]
        result = plan(
            ["level_2", "behavior_change", "ambiguous_failure", "symptom", "invariant", "remote_write", "replacement"],
            max_active=4,
            required_facts=required,
        )
        self.assertTrue(result["blocked"])
        self.assertTrue(result["deferred_mandatory"])
        self.assertTrue(any(item["capability"] != "acceptance_coverage" for item in result["deferred_mandatory"]))
        self.assertTrue(any(item["status"] == "blocked" for item in result["capability_status"]))
        self.assertTrue(result["missing_required_facts"])

    def test_new_evidence_replans_without_replaying_the_original_plan(self) -> None:
        initial_facts = ["level_1", "behavior_change"]
        initial = plan(initial_facts)
        expanded = plan(
            [*initial_facts, "external_boundary", "blind_spot"],
            previous_facts=initial_facts,
        )
        self.assertNotIn("observability", initial["selected"])
        self.assertIn("observability", expanded["selected"])
        self.assertTrue(expanded["replan_events"])
        self.assertEqual(len(expanded["replan_events"]), 1)
        self.assertEqual(expanded["replan_events"][0]["added_facts"], ["blind_spot", "external_boundary"])
        self.assertTrue(expanded["search_rounds"])
        self.assertNotEqual(initial["selected"], expanded["selected"])

    def test_default_preview_is_non_empty_and_respects_mandatory_budget(self) -> None:
        result = plan(["level_1", "behavior_change", "replacement"])
        self.assertTrue(result["selected"])
        self.assertLessEqual(len(result["selected"]), 6)
        self.assertTrue(
            {"risk_triage", "owner_mapping", "contract_tests", "retirement_cleanup", "evidence_ledger"}.issubset(
                result["selected"]
            )
        )
        required_fields = {"capability", "status", "triggered_by", "missing_requirements", "deferred_reason"}
        self.assertTrue(all(required_fields <= set(item) for item in result["capability_status"]))

    def test_required_fact_coverage_is_a_hard_acceptance_gate(self) -> None:
        result = plan(["level_1", "behavior_change"], required_facts=["owner_located", "human_signoff"])
        self.assertTrue(result["blocked"])
        self.assertIn("human_signoff", result["missing_required_facts"])
        self.assertIn("acceptance_coverage", {item["capability"] for item in result["deferred_mandatory"]})

    def test_narrow_acceptance_cannot_bypass_triggered_mandatory_capabilities(self) -> None:
        result = plan(["level_1", "behavior_change"], required_facts=["owner_located"])
        self.assertFalse(result["blocked"])
        self.assertTrue(
            {"risk_triage", "owner_mapping", "contract_tests", "retirement_cleanup", "evidence_ledger"}.issubset(
                result["selected"]
            )
        )
        self.assertFalse(result["deferred_mandatory"])

    def test_unresolved_mandatory_capability_blocks_completion(self) -> None:
        result = plan(["level_1", "behavior_change", "ambiguous_failure"])
        self.assertTrue(result["blocked"])
        causal = next(item for item in result["capability_status"] if item["capability"] == "causal_diagnosis")
        self.assertEqual(causal["status"], "unknown")
        self.assertIn("invariant", causal["missing_requirements"])

    def test_causal_output_unlocks_observability_when_node_evidence_is_required(self) -> None:
        result = plan(
            ["level_1", "behavior_change", "ambiguous_failure", "symptom", "invariant"],
            required_facts=["causal_owner_candidate", "node_evidence"],
            max_active=7,
        )
        self.assertFalse(result["blocked"])
        self.assertIn("causal_diagnosis", result["selected"])
        self.assertIn("observability", result["selected"])
        observability = next(item for item in result["transitions"] if item["capability"] == "observability")
        self.assertIn("hypotheses_recorded", observability["consumed"])
        self.assertIn("hypotheses_recorded", next(item for item in result["capability_status"] if item["capability"] == "observability")["triggered_by"])

    def test_replan_budget_rejects_a_third_evidence_driven_replan(self) -> None:
        with self.assertRaisesRegex(ValueError, "replan budget exhausted"):
            _ = plan(
                ["level_1", "behavior_change", "external_boundary"],
                previous_facts=["level_1", "behavior_change"],
                prior_replans=2,
            )

    def test_candidate_plans_are_bounded_and_machine_readable(self) -> None:
        result = plan(
            [
                "level_2",
                "behavior_change",
                "ambiguous_failure",
                "symptom",
                "invariant",
                "external_boundary",
                "external_dependency",
                "replacement",
                "cross_boundary",
            ],
            required_facts=["causal_owner_candidate", "node_evidence"],
        )
        self.assertGreaterEqual(len(result["candidate_plans"]), 1)
        self.assertLessEqual(len(result["candidate_plans"]), 3)
        for candidate in result["candidate_plans"]:
            self.assertIn("selected", candidate)
            self.assertIn("covered_required_facts", candidate)
            self.assertIn("missing_required_facts", candidate)
            self.assertIn("score", candidate)
        self.assertEqual(result["replan_events"], [])
        self.assertTrue(result["search_rounds"])

    def test_cli_emits_machine_readable_plan_for_a_checked_in_fixture(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "plan_capability_composition.py"),
                str(ROOT / "examples" / "capability-composition" / "rename.json"),
                "--max-active",
                "6",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["schema_version"], 1)
        self.assertFalse(payload["blocked"])
        self.assertIn("retirement_cleanup", payload["selected"])
        self.assertEqual(payload["missing_required_facts"], [])
        self.assertLessEqual(len(payload["candidate_plans"]), 3)
        self.assertTrue(all("capability" in item and "produced" in item for item in payload["transitions"]))


if __name__ == "__main__":
    _ = unittest.main()
