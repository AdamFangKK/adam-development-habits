"""canonical_contract_cleanup_v10_decision_retention_dynamic_retain_18; owner: policy.canonical_normalize; invariant: normalized lowercase output."""

def canonical_normalize(value):
    return value.strip().lower()

def evaluate(value):
    return canonical_normalize(value)
