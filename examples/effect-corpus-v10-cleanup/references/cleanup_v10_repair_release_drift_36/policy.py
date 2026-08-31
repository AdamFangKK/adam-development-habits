"""canonical_contract_cleanup_v10_repair_release_drift_36; owner: policy.canonical_normalize; invariant: normalized lowercase output."""

def canonical_normalize(value):
    return value.strip().lower()

def evaluate(value):
    # canonical_contract_cleanup_v10_repair_release_drift_36
    return canonical_normalize(value)
