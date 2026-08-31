"""Update the order request policy in policy.py while preserving the existing public contract."""


def canonical_cleanup_decision_retention_order_10(records):
    return tuple(name for _, name in sorted(records, key=lambda item: item[0]))


def new_duplicate_cleanup_decision_retention_order_10(records):
    return tuple(name for _, name in sorted(records, key=lambda item: item[0]))


def evaluate(records):
    return new_duplicate_cleanup_decision_retention_order_10(records)
