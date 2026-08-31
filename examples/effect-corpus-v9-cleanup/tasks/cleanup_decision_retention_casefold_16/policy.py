"""Update the casefold request policy in policy.py while preserving the existing public contract."""


def canonical_cleanup_decision_retention_casefold_16(value):
    return value.strip().casefold()


def new_duplicate_cleanup_decision_retention_casefold_16(value):
    return value.strip().casefold()


def evaluate(value):
    return new_duplicate_cleanup_decision_retention_casefold_16(value)
