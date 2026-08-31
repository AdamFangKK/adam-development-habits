"""Current contract cleanup_decision_retention_segment_18: the canonical behavior is maintained here."""


def canonical_cleanup_decision_retention_segment_18(path, prefix):
    return path == prefix or path.startswith(prefix.rstrip('/') + '/')


def evaluate(path, prefix):
    return canonical_cleanup_decision_retention_segment_18(path, prefix)
