"""Update the trim request policy in policy.py while preserving the existing public contract."""


def canonical_cleanup_decision_retention_trim_07(value):
    return value.strip()


def new_duplicate_cleanup_decision_retention_trim_07(value):
    return value.strip()


def evaluate(value):
    return new_duplicate_cleanup_decision_retention_trim_07(value)
