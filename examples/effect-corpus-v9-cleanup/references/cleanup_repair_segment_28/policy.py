"""Replace the obsolete segment implementation with the canonical contract. Keep the public behavior correct and update the implementation in policy.py."""


def canonical_cleanup_repair_segment_28(path, prefix):
    return path == prefix or path.startswith(prefix.rstrip('/') + '/')


def evaluate(path, prefix):
    return canonical_cleanup_repair_segment_28(path, prefix)
