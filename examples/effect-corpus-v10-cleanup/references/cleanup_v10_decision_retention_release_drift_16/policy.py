"""canonical_contract_cleanup_v10_decision_retention_release_drift_16; owner: policy.canonical_normalize; invariant: normalized lowercase output."""

def canonical_normalize(value):
    return value.strip().lower()

def evaluate(value):
    # canonical_contract_cleanup_v10_decision_retention_release_drift_16
    return canonical_normalize(value)
