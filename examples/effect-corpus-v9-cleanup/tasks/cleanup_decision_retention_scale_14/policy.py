"""Update the scale request policy in policy.py while preserving the existing public contract."""

EXTERNAL_REGISTRY = {"external_adapter_cleanup_decision_retention_scale_14": "canonical_cleanup_decision_retention_scale_14"}


def external_adapter_cleanup_decision_retention_scale_14(minor, scale):
    return minor / (10 ** scale)


def canonical_cleanup_decision_retention_scale_14(minor, scale):
    return minor / (10 ** scale)


def evaluate(minor, scale):
    # stale compatibility note cleanup_decision_retention_scale_14
    return canonical_cleanup_decision_retention_scale_14(minor, scale)
