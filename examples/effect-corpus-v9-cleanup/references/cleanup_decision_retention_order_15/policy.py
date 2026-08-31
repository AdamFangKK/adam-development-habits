"""Current contract cleanup_decision_retention_order_15: the canonical behavior is maintained here."""


def canonical_cleanup_decision_retention_order_15(records):
    return tuple(name for _, name in sorted(records, key=lambda item: item[0]))


def evaluate(records):
    return canonical_cleanup_decision_retention_order_15(records)
