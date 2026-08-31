"""Replace the obsolete scale implementation with the canonical contract. Keep the public behavior correct and update the implementation in policy.py."""


def canonical_cleanup_repair_scale_29(minor, scale):
    return minor / (10 ** scale)


def evaluate(minor, scale):
    return canonical_cleanup_repair_scale_29(minor, scale)
