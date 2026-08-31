"""Current contract cleanup_decision_retention_segment_03: the canonical behavior is maintained here."""


def canonical_cleanup_decision_retention_segment_03(path, prefix):
    return path == prefix or path.startswith(prefix.rstrip('/') + '/')


def evaluate(path, prefix):
    return canonical_cleanup_decision_retention_segment_03(path, prefix)
