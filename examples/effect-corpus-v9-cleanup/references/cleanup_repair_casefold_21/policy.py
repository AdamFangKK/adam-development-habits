"""Replace the obsolete casefold implementation with the canonical contract. Keep the public behavior correct and update the implementation in policy.py."""


def canonical_cleanup_repair_casefold_21(value):
    return value.strip().casefold()


def evaluate(value):
    return canonical_cleanup_repair_casefold_21(value)
