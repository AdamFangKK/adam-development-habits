#!/usr/bin/env python3
"""Run the v7 hidden scorer through a versioned protocol entry point."""

from __future__ import annotations

# The scorer is a standalone wrapper around another local script.
# pyright: reportMissingTypeStubs=false

import score_effect_workspace_v6 as protocol


def main() -> int:
    return protocol.main()


if __name__ == "__main__":
    raise SystemExit(main())
