"""legacy_contract_cleanup_v10_decision_retention_dynamic_retain_06."""

def canonical_normalize(value):
    return value.strip().lower()

def evaluate(value):
    return canonical_normalize(value)
