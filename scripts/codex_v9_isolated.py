#!/usr/bin/env python3
"""Invoke Codex with the V9 Skill-search isolation flag."""

from __future__ import annotations

import os
import sys


def inject_skill_search_disable(arguments: list[str]) -> list[str]:
    """Add the shared V9 flag exactly once to a `codex exec` invocation."""
    if not arguments or arguments[0] != "exec":
        return list(arguments)
    for index, argument in enumerate(arguments[:-1]):
        if argument == "--disable" and arguments[index + 1] == "skill_search":
            return list(arguments)
    return [arguments[0], "--disable", "skill_search", *arguments[1:]]


def main() -> int:
    codex = os.environ.get("ADAM_V9_CODEX_BINARY", "")
    if not codex or not os.path.isfile(codex):
        print("V9 isolation wrapper requires ADAM_V9_CODEX_BINARY", file=sys.stderr)
        return 127
    arguments = inject_skill_search_disable(sys.argv[1:])
    print("V9 isolation wrapper: --disable skill_search", file=sys.stderr, flush=True)
    os.execv(codex, [codex, *arguments])


if __name__ == "__main__":
    raise SystemExit(main())
