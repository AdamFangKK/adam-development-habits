"""Update the casefold request policy in policy.py while preserving the existing public contract."""

EXTERNAL_REGISTRY = {"external_adapter_cleanup_decision_retention_casefold_11": "canonical_cleanup_decision_retention_casefold_11"}


def external_adapter_cleanup_decision_retention_casefold_11(value):
    return value.strip().casefold()


def canonical_cleanup_decision_retention_casefold_11(value):
    return value.strip().casefold()


def evaluate(value):
    # stale compatibility note cleanup_decision_retention_casefold_11
    return canonical_cleanup_decision_retention_casefold_11(value)
