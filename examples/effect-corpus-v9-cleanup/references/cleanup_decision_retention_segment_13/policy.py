"""Update the segment request policy in policy.py while preserving the existing public contract."""


def canonical_cleanup_decision_retention_segment_13(path, prefix):
    return path == prefix or path.startswith(prefix.rstrip('/') + '/')


def evaluate(path, prefix):
    return canonical_cleanup_decision_retention_segment_13(path, prefix)
