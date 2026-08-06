#!/usr/bin/env python3
"""Combine a frozen preregistration and runner output into a completed record."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import cast


def load_object(path: Path) -> dict[str, object]:
    value = cast(object, json.loads(path.read_text(encoding="utf-8")))
    if not isinstance(value, dict):
        raise SystemExit(f"{path} must contain a JSON object")
    return cast(dict[str, object], value)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    _ = parser.add_argument("--preregistration", type=Path, required=True)
    _ = parser.add_argument("--trials", type=Path, required=True)
    _ = parser.add_argument("--git-commit", required=True)
    _ = parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    preregistration = load_object(cast(Path, arguments.preregistration))
    trial_bundle = load_object(cast(Path, arguments.trials))
    if preregistration.get("status") != "planned" or preregistration.get("trials") != []:
        raise SystemExit("preregistration must be frozen in planned state with no trials")
    trials = trial_bundle.get("trials")
    if not isinstance(trials, list):
        raise SystemExit("trial bundle must contain a trials list")
    record = dict(preregistration)
    record["status"] = "completed"
    registration = cast(dict[str, object], record["preregistration"])
    registration["git_commit"] = cast(str, arguments.git_commit)
    registration["recorded_before_first_trial"] = True
    record["trials"] = trials
    record["runner_metadata"] = {key: value for key, value in trial_bundle.items() if key != "trials"}
    output = cast(Path, arguments.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    _ = output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
