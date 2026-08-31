#!/usr/bin/env python3
"""Validate bounded, redacted development/runtime checkpoint events."""

from __future__ import annotations

import argparse
import json
import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any, cast


OUTCOMES = {"planned", "executed", "verified", "blocked"}
CLASSIFICATIONS = {"remove", "retain", "unknown", "reuse_existing_owner", "not_applicable"}
LEVEL_ONE_EVENTS = {"owner_located", "retirement_classified", "verification_completed"}
LEVEL_TWO_EVENTS = {"started", "owner_located", "implemented", "cleanup_classified", "verified", "committed"}
LEVEL_TWO_ORDER = ("started", "owner_located", "implemented", "cleanup_classified", "verified", "committed")
EVENT_NAME = re.compile(r"^[a-z][a-z0-9_]{2,63}$")
FORBIDDEN_TOKENS = (
    "secret",
    "token",
    "password",
    "raw_payload",
    "payload",
    "personal_data",
    "source_text",
    "user_id",
    "email",
    "phone",
    "unbounded_user_label",
    "label_values",
)
REQUIRED_FIELDS = ("event", "change_id", "component", "outcome", "classification", "evidence_id")


def _contains_forbidden_key(value: Any, path: str = "") -> str | None:
    if isinstance(value, dict):
        for key, nested in value.items():
            key_text = str(key).lower()
            if any(token in key_text for token in FORBIDDEN_TOKENS):
                return f"forbidden sensitive or unbounded field at {path + '.' if path else ''}{key}"
            found = _contains_forbidden_key(nested, f"{path}.{key}" if path else str(key))
            if found:
                return found
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            found = _contains_forbidden_key(nested, f"{path}[{index}]")
            if found:
                return found
    return None


def _validate_event(event: Any, index: int) -> list[str]:
    errors: list[str] = []
    if not isinstance(event, dict):
        return [f"event {index} must be an object"]
    data = cast(dict[str, Any], event)
    forbidden = _contains_forbidden_key(data)
    if forbidden:
        errors.append(f"event {index}: {forbidden}")
    for field in REQUIRED_FIELDS:
        if not isinstance(data.get(field), str) or not data[field].strip():
            errors.append(f"event {index}.{field} must be non-empty text")
    if isinstance(data.get("event"), str) and not EVENT_NAME.fullmatch(data["event"]):
        errors.append(f"event {index}.event must be a stable snake_case name")
    if data.get("outcome") not in OUTCOMES:
        errors.append(f"event {index}.outcome must be planned, executed, verified, or blocked")
    if data.get("classification") not in CLASSIFICATIONS:
        errors.append(f"event {index}.classification is outside the bounded vocabulary")
    duration = data.get("duration_ms")
    if duration is not None and (not isinstance(duration, (int, float)) or isinstance(duration, bool) or duration < 0):
        errors.append(f"event {index}.duration_ms must be a non-negative number")
    labels = data.get("labels")
    if labels is not None and (
        not isinstance(labels, list)
        or len(labels) > 8
        or any(not isinstance(label, str) or not re.fullmatch(r"[a-z][a-z0-9_]{1,31}", label) for label in labels)
    ):
        errors.append(f"event {index}.labels must contain at most eight bounded snake_case names")
    return errors


def validate_events(events: Iterable[Any], *, level: int) -> list[str]:
    values = list(events)
    errors: list[str] = []
    if level not in {0, 1, 2}:
        return ["level must be 0, 1, or 2"]
    if level == 0:
        if values:
            errors.append("level 0 must not emit instrumentation events")
        return errors
    seen: set[tuple[str, str, str]] = set()
    names: set[str] = set()
    ordered_names: list[str] = []
    for index, event in enumerate(values):
        errors.extend(_validate_event(event, index))
        if isinstance(event, dict):
            data = cast(dict[str, Any], event)
            key = (str(data.get("change_id", "")), str(data.get("component", "")), str(data.get("event", "")))
            if key in seen:
                errors.append(f"event {index}: duplicate logical transition {key[2]}")
            seen.add(key)
            if isinstance(data.get("event"), str):
                names.add(data["event"])
                ordered_names.append(data["event"])
    required = LEVEL_ONE_EVENTS if level == 1 else LEVEL_TWO_EVENTS
    missing = sorted(required - names)
    if missing:
        errors.append(f"missing required level {level} events: {', '.join(missing)}")
    if level == 2 and not missing:
        positions = [ordered_names.index(name) for name in LEVEL_TWO_ORDER]
        if positions != sorted(positions):
            errors.append("level 2 lifecycle events must be ordered started -> owner_located -> implemented -> cleanup_classified -> verified -> committed")
    return errors


def load_events(path: Path) -> list[Any]:
    events: list[Any] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError as error:
            raise ValueError(f"line {line_number} is not valid JSON: {error.msg}") from error
    return events


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    _ = parser.add_argument("--events", type=Path, required=True)
    _ = parser.add_argument("--level", type=int, required=True, choices=(0, 1, 2))
    arguments = parser.parse_args()
    try:
        events = load_events(arguments.events)
        errors = validate_events(events, level=arguments.level)
    except (OSError, ValueError) as error:
        print(json.dumps({"valid": False, "errors": [str(error)]}, indent=2))
        return 1
    report = {"valid": not errors, "level": arguments.level, "event_count": len(events), "errors": errors}
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
