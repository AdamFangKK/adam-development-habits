"""canonical_contract_cleanup_v10_repair_release_drift_32; owner: policy.canonical_normalize; invariant: normalized lowercase output."""

def canonical_normalize(value):
    return value.strip().lower()

def evaluate(value):
    # canonical_contract_cleanup_v10_repair_release_drift_32
    return canonical_normalize(value)
