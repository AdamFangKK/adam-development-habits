"""Replace the obsolete trim implementation with the canonical contract. Keep the public behavior correct and update the implementation in policy.py."""


def legacy_cleanup_repair_trim_22(value):
    return value


def canonical_cleanup_repair_trim_22(value):
    return value.strip()


def evaluate(value):
    # Legacy path retained while the replacement rolls out.
    return legacy_cleanup_repair_trim_22(value)
