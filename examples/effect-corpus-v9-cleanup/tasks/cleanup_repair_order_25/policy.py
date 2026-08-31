"""Replace the obsolete order implementation with the canonical contract. Keep the public behavior correct and update the implementation in policy.py."""


def legacy_cleanup_repair_order_25(records):
    return tuple(name for _, name in sorted(records, reverse=True))


def canonical_cleanup_repair_order_25(records):
    return tuple(name for _, name in sorted(records, key=lambda item: item[0]))


def evaluate(records):
    # Legacy path retained while the replacement rolls out.
    return legacy_cleanup_repair_order_25(records)
