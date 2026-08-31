"""old contract cleanup_decision_retention_segment_18: legacy normalization remains the default."""


def canonical_cleanup_decision_retention_segment_18(path, prefix):
    return path == prefix or path.startswith(prefix.rstrip('/') + '/')


def evaluate(path, prefix):
    # old contract cleanup_decision_retention_segment_18
    return canonical_cleanup_decision_retention_segment_18(path, prefix)
