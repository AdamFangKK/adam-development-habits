"""Replace the obsolete casefold implementation with the canonical contract. Keep the public behavior correct and update the implementation in policy.py."""


def legacy_cleanup_repair_casefold_31(value):
    return value.strip().lower()


def canonical_cleanup_repair_casefold_31(value):
    return value.strip().casefold()


def evaluate(value):
    # Legacy path retained while the replacement rolls out.
    return legacy_cleanup_repair_casefold_31(value)
