"""old contract cleanup_decision_retention_casefold_06: legacy normalization remains the default."""


def canonical_cleanup_decision_retention_casefold_06(value):
    return value.strip().casefold()


def evaluate(value):
    # old contract cleanup_decision_retention_casefold_06
    return canonical_cleanup_decision_retention_casefold_06(value)
