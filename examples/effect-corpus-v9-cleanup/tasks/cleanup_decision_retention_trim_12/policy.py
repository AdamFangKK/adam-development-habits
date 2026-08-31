"""old contract cleanup_decision_retention_trim_12: legacy normalization remains the default."""


def canonical_cleanup_decision_retention_trim_12(value):
    return value.strip()


def evaluate(value):
    # old contract cleanup_decision_retention_trim_12
    return canonical_cleanup_decision_retention_trim_12(value)
