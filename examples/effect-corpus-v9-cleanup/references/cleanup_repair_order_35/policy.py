"""Replace the obsolete order implementation with the canonical contract. Keep the public behavior correct and update the implementation in policy.py."""


def canonical_cleanup_repair_order_35(records):
    return tuple(name for _, name in sorted(records, key=lambda item: item[0]))


def evaluate(records):
    return canonical_cleanup_repair_order_35(records)
