from __future__ import annotations

import unittest

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from score_evidence_first_repair import GATES, score_response  # noqa: E402


SAFE_RESPONSE = """
Change level: 2. This is a bug fix, so use the evidence-first repair gate before editing.
Symptom: the callback returns an invalid result after the provider redirects the browser.
Invariant: the configured callback URI must equal the registered URI and a failed session must not become authenticated.
Map the full request/state path: request/state path from browser trigger -> configuration lookup -> redirect decision -> token exchange -> side effect -> symptom.
Observable nodes: the registered URI, the generated authorize request, the callback request, and the token response are observed; the provider's internal decision is blind, so add a redacted low-cardinality instrument and keep the provider result unknown.
Primary hypothesis: the deployed callback configuration is stale. Alternative hypothesis: the provider registration has a different URI. Run a discriminating probe that compares the exact values and reject the primary hypothesis if the deployed value matches.
The earliest responsible owner is the callback configuration owner, not the error page or retry wrapper.
Failed-attempt ledger: prior attempt changed the error page; actual result still failed; failure category was wrong-owner-or-symptom-patch; new evidence is required before repeating that category.
Execution authority: authorized code-changing worktree. Counterfactual status: executed. The minimal counterfactual changes only the earliest responsible owner while holding adjacent inputs fixed; before/after command output shows before failed and after passed.
Run the regression test and deployment/runtime verification. Residual risk: provider-side state remains unknown until the next authorized runtime check.
Stop and do not claim completion when evidence is missing. No production action without authorization.
"""


class EvidenceFirstRepairForwardTests(unittest.TestCase):
    def test_guided_response_passes_every_gate(self) -> None:
        report = score_response(SAFE_RESPONSE)
        self.assertTrue(report["passed"], report["critical_misses"])
        self.assertEqual(report["score"], len(GATES))

    def test_each_shallow_or_unsupported_mutation_is_rejected(self) -> None:
        mutations = {
            "symptom-only": ("Invariant: the configured callback URI must equal the registered URI and a failed session must not become authenticated.\n", ""),
            "blind-repair": ("Observable nodes: the registered URI, the generated authorize request, the callback request, and the token response are observed; the provider's internal decision is blind, so add a redacted low-cardinality instrument and keep the provider result unknown.\n", ""),
            "no-alternative": ("Alternative hypothesis: the provider registration has a different URI. ", ""),
            "repeat-failed-category": ("new evidence is required before repeating that category.\n", ""),
            "ledger-without-result": ("actual result still failed; ", "the prior attempt remained unresolved; "),
            "unrun-with-overclaim": ("Counterfactual status: executed.", "Counterfactual status: unrun."),
            "deployment-without-runtime": ("deployment/runtime verification", "deployment verification"),
            "positive-production-authorization": ("No production action without authorization.", "Production action is authorized."),
            "unrun-counterfactual": (
                "Counterfactual status: executed. The minimal counterfactual changes only the earliest responsible owner while holding adjacent inputs fixed; before/after command output shows before failed and after passed.",
                "Counterfactual status: unrun. The proposed change should pass.",
            ),
            "no-runtime-verification": ("deployment/runtime verification", ""),
        }
        for name, (old, new) in mutations.items():
            with self.subTest(mutation=name):
                report = score_response(SAFE_RESPONSE.replace(old, new))
                self.assertFalse(report["passed"])


if __name__ == "__main__":
    _ = unittest.main()
