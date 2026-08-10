#!/usr/bin/env python3
"""Run the V8 blind hidden scorer through a versioned entry point."""

# pyright: reportMissingTypeStubs=false

from __future__ import annotations

import score_effect_workspace_v6 as protocol


def main() -> int:
    return protocol.main()


if __name__ == "__main__":
    raise SystemExit(main())
