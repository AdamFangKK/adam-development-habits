"""Replace the obsolete scale implementation with the canonical contract. Keep the public behavior correct and update the implementation in policy.py."""


def legacy_cleanup_repair_scale_34(minor, scale):
    return minor / 100


def canonical_cleanup_repair_scale_34(minor, scale):
    return minor / (10 ** scale)


def evaluate(minor, scale):
    # Legacy path retained while the replacement rolls out.
    return legacy_cleanup_repair_scale_34(minor, scale)
