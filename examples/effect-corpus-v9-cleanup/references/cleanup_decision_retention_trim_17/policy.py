"""Update the trim request policy in policy.py while preserving the existing public contract."""

EXTERNAL_REGISTRY = {"external_adapter_cleanup_decision_retention_trim_17": "canonical_cleanup_decision_retention_trim_17"}


def external_adapter_cleanup_decision_retention_trim_17(value):
    return value.strip()


def canonical_cleanup_decision_retention_trim_17(value):
    return value.strip()


def evaluate(value):
    return canonical_cleanup_decision_retention_trim_17(value)
