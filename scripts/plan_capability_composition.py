#!/usr/bin/env python3
"""Build a bounded, evidence-oriented capability plan without external dependencies."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = ROOT / "references" / "capability-catalog.json"


def _string_list(value: Any, field: str, capability_id: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise ValueError(f"{capability_id}.{field} must be a list of non-empty strings")
    return list(value)


def load_catalog(path: Path = DEFAULT_CATALOG) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ValueError("capability catalog must use schema_version 1")
    raw_capabilities = payload.get("capabilities")
    if not isinstance(raw_capabilities, list) or not raw_capabilities:
        raise ValueError("capability catalog must contain capabilities")

    capabilities: list[dict[str, Any]] = []
    identifiers: set[str] = set()
    for raw in raw_capabilities:
        if not isinstance(raw, dict):
            raise ValueError("every capability must be an object")
        identifier = raw.get("id")
        if not isinstance(identifier, str) or not identifier:
            raise ValueError("capability id must be a non-empty string")
        if identifier in identifiers:
            raise ValueError(f"duplicate capability id: {identifier}")
        identifiers.add(identifier)
        for field in ("purpose", "trigger_any", "requires_all", "requires_any", "produces"):
            if field == "purpose":
                if not isinstance(raw.get(field), str) or not raw[field]:
                    raise ValueError(f"{identifier}.purpose must be a non-empty string")
            else:
                _string_list(raw.get(field), field, identifier)
        if "mandatory_if" in raw:
            _string_list(raw["mandatory_if"], "mandatory_if", identifier)
        for field in ("cost", "risk_reduction"):
            value = raw.get(field)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(f"{identifier}.{field} must be a non-negative integer")
        if "priority" in raw and (
            not isinstance(raw["priority"], int) or isinstance(raw["priority"], bool) or raw["priority"] < 0
        ):
            raise ValueError(f"{identifier}.priority must be a non-negative integer")
        for field in ("excludes",):
            if field in raw:
                _string_list(raw[field], field, identifier)
        capabilities.append(raw)
    return capabilities


def _candidate_reason(card: dict[str, Any], facts: set[str]) -> tuple[bool, str, set[str], set[str]]:
    triggers = set(card["trigger_any"])
    trigger_matches = triggers.intersection(facts)
    if not trigger_matches:
        return False, "no trigger fact", trigger_matches, set()
    missing_all = set(card["requires_all"]).difference(facts)
    if missing_all:
        return False, "missing required facts: " + ", ".join(sorted(missing_all)), trigger_matches, missing_all
    requires_any = set(card["requires_any"])
    if requires_any and not requires_any.intersection(facts):
        return False, "requires one of: " + ", ".join(sorted(requires_any)), trigger_matches, requires_any
    excluded = set(card.get("excludes", [])).intersection(facts)
    if excluded:
        return False, "excluded by facts: " + ", ".join(sorted(excluded)), trigger_matches, set()
    return True, f"triggered by: {', '.join(sorted(trigger_matches))}", trigger_matches, set()


def _score(card: dict[str, Any], facts: set[str], trigger_matches: set[str]) -> int:
    produced_new = set(card["produces"]).difference(facts)
    return (
        int(card.get("priority", 50))
        + int(card["risk_reduction"]) * 10
        + len(produced_new) * 3
        + len(trigger_matches)
        - int(card["cost"])
    )


def _is_mandatory(card: dict[str, Any], facts: set[str]) -> bool:
    return bool(set(card.get("mandatory_if", [])).intersection(facts))


def plan(
    facts: Iterable[str],
    *,
    catalog_path: Path = DEFAULT_CATALOG,
    max_active: int | None = None,
    max_rounds: int = 16,
    required_facts: Iterable[str] = (),
    beam_width: int = 3,
    previous_facts: Iterable[str] | None = None,
    prior_replans: int = 0,
) -> dict[str, Any]:
    initial_facts = {fact for fact in facts if isinstance(fact, str) and fact}
    required = {fact for fact in required_facts if isinstance(fact, str) and fact}
    prior_facts = None if previous_facts is None else {fact for fact in previous_facts if isinstance(fact, str) and fact}
    if max_active is None:
        max_active = 10 if "level_2" in initial_facts else 6
    if max_active < 1:
        raise ValueError("max_active must be at least 1")
    if max_rounds < 1:
        raise ValueError("max_rounds must be at least 1")
    if beam_width < 1 or beam_width > 3:
        raise ValueError("beam_width must be between 1 and 3")
    if prior_replans < 0 or prior_replans > 2:
        raise ValueError("prior_replans must be between 0 and 2")
    if prior_facts is not None and prior_facts != initial_facts and prior_replans >= 2:
        raise ValueError("replan budget exhausted; record a new evidence budget before replanning")
    cards = load_catalog(catalog_path)

    def coverage(state: dict[str, Any]) -> set[str]:
        return required.intersection(state["facts"])

    def mandatory_count(state: dict[str, Any]) -> int:
        return sum(1 for transition in state["transitions"] if transition["mandatory"])

    def pending_mandatory(state: dict[str, Any]) -> list[dict[str, Any]]:
        return [
            card
            for card in cards
            if str(card["id"]) not in state["selected"] and _is_mandatory(card, state["facts"])
        ]

    def is_terminal(state: dict[str, Any]) -> bool:
        return (not required or required.issubset(state["facts"])) and not pending_mandatory(state)

    def rank(state: dict[str, Any]) -> tuple[int, int, int, int, tuple[str, ...]]:
        # Required facts drive the search when supplied. Otherwise, mandatory
        # gates and risk reduction keep the default preview useful instead of
        # treating the empty initial state as a complete plan.
        if required:
            return (
                len(coverage(state)),
                mandatory_count(state),
                -len(state["selected"]),
                state["score"],
                tuple(state["selected"]),
            )
        return (
            mandatory_count(state),
            state["score"],
            -len(state["selected"]),
            0,
            tuple(state["selected"]),
        )

    beam: list[dict[str, Any]] = [
        {"selected": [], "facts": set(initial_facts), "transitions": [], "score": 0}
    ]
    terminal: list[dict[str, Any]] = []
    search_rounds: list[dict[str, Any]] = []
    for round_number in range(max_rounds):
        next_states: list[dict[str, Any]] = []
        for state in beam:
            if is_terminal(state):
                terminal.append(state)
                continue
            if len(state["selected"]) >= max_active:
                continue
            for card in cards:
                identifier = str(card["id"])
                if identifier in state["selected"]:
                    continue
                eligible, reason, trigger_matches, _ = _candidate_reason(card, state["facts"])
                if not eligible:
                    continue
                produced = sorted(set(card["produces"]).difference(state["facts"]))
                if not produced:
                    continue
                consumed = sorted(set(card["requires_all"]).intersection(state["facts"]) | trigger_matches)
                next_states.append(
                    {
                        "selected": [*state["selected"], identifier],
                        "facts": set(state["facts"]).union(produced),
                        "transitions": [
                            *state["transitions"],
                            {
                                "capability": identifier,
                                "consumed": consumed,
                                "produced": produced,
                                "score": _score(card, state["facts"], trigger_matches),
                                "mandatory": _is_mandatory(card, state["facts"]),
                                "reason": reason,
                            },
                        ],
                        "score": state["score"] + _score(card, state["facts"], trigger_matches),
                    }
                )
        if not next_states:
            break
        unique: dict[tuple[str, ...], dict[str, Any]] = {}
        for state in next_states:
            key = tuple(state["selected"])
            previous = unique.get(key)
            if previous is None or rank(state) > rank(previous):
                unique[key] = state
        beam = sorted(unique.values(), key=rank, reverse=True)[:beam_width]
        search_rounds.append(
            {
                "round": round_number + 1,
                "reason": "new produced facts changed eligible capabilities",
                "candidate_count": len(unique),
                "retained_count": len(beam),
                "retained_plans": [state["selected"] for state in beam],
            }
        )

    if required:
        terminal.extend(state for state in beam if is_terminal(state))
    else:
        # With no explicit acceptance facts, the surviving beam states are the
        # bounded preview candidates; the initial empty state is never a plan.
        terminal.extend(beam)
    candidates = sorted({tuple(state["selected"]): state for state in terminal + beam}.values(), key=rank, reverse=True)
    chosen = candidates[0] if candidates else {"selected": [], "facts": set(initial_facts), "transitions": [], "score": 0}
    selected = chosen["selected"]
    current_facts = chosen["facts"]
    candidate_plans = [
        {
            "selected": state["selected"],
            "covered_required_facts": sorted(coverage(state)),
            "missing_required_facts": sorted(required.difference(state["facts"])),
            "score": state["score"],
        }
        for state in candidates[:beam_width]
    ]
    capability_status: list[dict[str, Any]] = []
    deferred: list[dict[str, str]] = []
    for card in cards:
        identifier = str(card["id"])
        if identifier in selected:
            capability_status.append(
                {
                    "capability": identifier,
                    "status": "selected",
                    "triggered_by": sorted(set(card["trigger_any"]).intersection(initial_facts | current_facts)),
                    "missing_requirements": [],
                    "deferred_reason": None,
                }
            )
            continue
        eligible, reason, trigger_matches, missing = _candidate_reason(card, current_facts)
        if not trigger_matches:
            status = "not_applicable"
            deferred_reason = reason
        elif not eligible:
            status = "unknown"
            deferred_reason = reason
        else:
            status = "deferred"
            deferred_reason = "not in the minimum-sufficient beam plan"
        if _is_mandatory(card, current_facts):
            status = "blocked" if eligible else "unknown"
            if eligible:
                deferred_reason = "active capability limit reached; mandatory capability deferred"
            else:
                deferred_reason = "mandatory capability lacks required evidence: " + ", ".join(sorted(missing))
            deferred.append({"capability": identifier, "reason": deferred_reason})
        capability_status.append(
            {
                "capability": identifier,
                "status": status,
                "triggered_by": sorted(trigger_matches),
                "missing_requirements": sorted(missing),
                "deferred_reason": deferred_reason,
            }
        )
    missing_required = sorted(required.difference(current_facts))
    if missing_required:
        deferred.append(
            {
                "capability": "acceptance_coverage",
                "reason": "required facts not produced: " + ", ".join(missing_required),
            }
        )

    replan_events: list[dict[str, Any]] = []
    if prior_facts is not None and prior_facts != initial_facts:
        replan_events.append(
            {
                "reason": "observed facts changed",
                "added_facts": sorted(initial_facts.difference(prior_facts)),
                "removed_facts": sorted(prior_facts.difference(initial_facts)),
                "prior_replans": prior_replans,
                "resulting_replans": prior_replans + 1,
            }
        )

    return {
        "schema_version": 1,
        "initial_facts": sorted(initial_facts),
        "selected": selected,
        "transitions": chosen["transitions"],
        "candidate_plans": candidate_plans,
        "capability_status": capability_status,
        "rejected": [item for item in capability_status if item["status"] != "selected"],
        "deferred_mandatory": deferred,
        "blocked": bool(deferred) or bool(missing_required),
        "replan_events": replan_events,
        "search_rounds": search_rounds,
        "required_facts": sorted(required),
        "covered_required_facts": sorted(required.intersection(current_facts)),
        "missing_required_facts": missing_required,
        "final_facts": sorted(current_facts),
        "limits": {"max_active": max_active, "max_rounds": max_rounds},
        "catalog": str(catalog_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan a bounded adaptive capability composition.")
    parser.add_argument("facts", type=Path, help="JSON object containing a non-empty or empty 'facts' list")
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--max-active", type=int, default=None)
    parser.add_argument("--max-rounds", type=int, default=16)
    parser.add_argument("--beam-width", type=int, default=3)
    args = parser.parse_args()
    payload = json.loads(args.facts.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("facts"), list):
        raise SystemExit("facts input must be a JSON object with a 'facts' list")
    print(
        json.dumps(
            plan(
                payload["facts"],
                catalog_path=args.catalog,
                max_active=args.max_active,
                max_rounds=args.max_rounds,
                required_facts=payload.get("required_facts", []),
                beam_width=args.beam_width,
                previous_facts=payload.get("previous_facts"),
                prior_replans=payload.get("prior_replans", 0),
            ),
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
