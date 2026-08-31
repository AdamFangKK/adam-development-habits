"""legacy_contract_cleanup_v10_decision_retention_semantic_duplicate_03."""

from helpers.cleanup_v10_decision_retention_semantic_duplicate_03_alias import normalize_alias

def canonical_normalize(value):
    return value.strip().lower()

def evaluate(value):
    return normalize_alias(value)
