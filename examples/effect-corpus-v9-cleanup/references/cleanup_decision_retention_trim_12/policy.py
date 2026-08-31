"""Current contract cleanup_decision_retention_trim_12: the canonical behavior is maintained here."""


def canonical_cleanup_decision_retention_trim_12(value):
    return value.strip()


def evaluate(value):
    return canonical_cleanup_decision_retention_trim_12(value)
