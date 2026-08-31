"""Replace the obsolete trim implementation with the canonical contract. Keep the public behavior correct and update the implementation in policy.py."""


def canonical_cleanup_repair_trim_37(value):
    return value.strip()


def evaluate(value):
    return canonical_cleanup_repair_trim_37(value)
