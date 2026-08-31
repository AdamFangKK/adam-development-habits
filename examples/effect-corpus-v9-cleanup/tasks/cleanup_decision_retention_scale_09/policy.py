"""old contract cleanup_decision_retention_scale_09: legacy normalization remains the default."""


def canonical_cleanup_decision_retention_scale_09(minor, scale):
    return minor / (10 ** scale)


def evaluate(minor, scale):
    # old contract cleanup_decision_retention_scale_09
    return canonical_cleanup_decision_retention_scale_09(minor, scale)
