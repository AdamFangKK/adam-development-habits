"""Current contract cleanup_decision_retention_scale_09: the canonical behavior is maintained here."""


def canonical_cleanup_decision_retention_scale_09(minor, scale):
    return minor / (10 ** scale)


def evaluate(minor, scale):
    return canonical_cleanup_decision_retention_scale_09(minor, scale)
