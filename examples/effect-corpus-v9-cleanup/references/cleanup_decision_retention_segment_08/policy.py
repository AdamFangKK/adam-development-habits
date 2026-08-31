"""Update the segment request policy in policy.py while preserving the existing public contract."""

EXTERNAL_REGISTRY = {"external_adapter_cleanup_decision_retention_segment_08": "canonical_cleanup_decision_retention_segment_08"}


def external_adapter_cleanup_decision_retention_segment_08(path, prefix):
    return path == prefix or path.startswith(prefix.rstrip('/') + '/')


def canonical_cleanup_decision_retention_segment_08(path, prefix):
    return path == prefix or path.startswith(prefix.rstrip('/') + '/')


def evaluate(path, prefix):
    return canonical_cleanup_decision_retention_segment_08(path, prefix)
