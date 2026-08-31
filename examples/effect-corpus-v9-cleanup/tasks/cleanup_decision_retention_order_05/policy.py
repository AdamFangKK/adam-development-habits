"""Update the order request policy in policy.py while preserving the existing public contract."""

EXTERNAL_REGISTRY = {"external_adapter_cleanup_decision_retention_order_05": "canonical_cleanup_decision_retention_order_05"}


def external_adapter_cleanup_decision_retention_order_05(records):
    return tuple(name for _, name in sorted(records, key=lambda item: item[0]))


def canonical_cleanup_decision_retention_order_05(records):
    return tuple(name for _, name in sorted(records, key=lambda item: item[0]))


def evaluate(records):
    # stale compatibility note cleanup_decision_retention_order_05
    return canonical_cleanup_decision_retention_order_05(records)
