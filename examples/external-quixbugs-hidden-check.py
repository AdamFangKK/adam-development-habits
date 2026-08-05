#!/usr/bin/env python3
"""Differentially verify a QuixBugs candidate against its pinned reference."""

from __future__ import annotations

import hashlib
import json
import runpy
import sys
from collections.abc import Callable
from copy import deepcopy
from pathlib import Path
from typing import cast


Edge = tuple[str, str]
Graph = dict[Edge, int]
ShortestPaths = Callable[[str, Graph], dict[str, float]]

CASES: tuple[Graph, ...] = (
    {("S", "A"): 1, ("X", "Y"): 7, ("Y", "X"): 5},
    {
        ("S", "A"): 8,
        ("S", "B"): 1,
        ("B", "A"): 2,
        ("A", "C"): 4,
        ("X", "Y"): 9,
        ("Y", "X"): 3,
    },
)


def load_shortest_paths(path: Path) -> ShortestPaths:
    namespace: dict[str, object] = runpy.run_path(str(path))
    function = namespace.get("shortest_paths")
    if not callable(function):
        raise TypeError(f"{path} does not define shortest_paths")
    return cast(ShortestPaths, function)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_arguments(arguments: list[str]) -> tuple[Path, Path, str]:
    if len(arguments) != 6 or arguments[0] != "--candidate" or arguments[2] != "--reference" or arguments[4] != "--label":
        raise SystemExit("usage: external-quixbugs-hidden-check.py --candidate PATH --reference PATH --label LABEL")
    return Path(arguments[1]), Path(arguments[3]), arguments[5]


def main(arguments: list[str]) -> int:
    candidate_path, reference_path, label = parse_arguments(arguments)
    candidate = load_shortest_paths(candidate_path)
    reference = load_shortest_paths(reference_path)
    for index, graph in enumerate(CASES, start=1):
        candidate_input = deepcopy(graph)
        expected = reference("S", deepcopy(graph))
        actual = candidate("S", candidate_input)
        if candidate_input != graph:
            raise AssertionError(f"case {index}: candidate mutated the input mapping")
        if actual != expected:
            raise AssertionError(f"case {index}: expected {expected}, got {actual}")

    report = {
        "candidate_label": label,
        "candidate_sha256": sha256(candidate_path),
        "case_count": len(CASES),
        "input_mapping_unchanged": True,
        "reference_sha256": sha256(reference_path),
        "result": "passed",
    }
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
