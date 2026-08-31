"""Update the scale request policy in policy.py while preserving the existing public contract."""


def canonical_cleanup_decision_retention_scale_19(minor, scale):
    return minor / (10 ** scale)


def evaluate(minor, scale):
    return canonical_cleanup_decision_retention_scale_19(minor, scale)
