"""legacy_contract_cleanup_v10_repair_semantic_duplicate_31."""

from helpers.cleanup_v10_repair_semantic_duplicate_31_alias import normalize_alias

def canonical_normalize(value):
    return value.strip().lower()

def evaluate(value):
    return normalize_alias(value)
