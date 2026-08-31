"""Replace the obsolete segment implementation with the canonical contract. Keep the public behavior correct and update the implementation in policy.py."""


def legacy_cleanup_repair_segment_38(path, prefix):
    return path.startswith(prefix)


def canonical_cleanup_repair_segment_38(path, prefix):
    return path == prefix or path.startswith(prefix.rstrip('/') + '/')


def evaluate(path, prefix):
    # Legacy path retained while the replacement rolls out.
    return legacy_cleanup_repair_segment_38(path, prefix)
