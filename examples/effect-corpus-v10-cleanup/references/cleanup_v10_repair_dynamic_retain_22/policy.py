"""canonical_contract_cleanup_v10_repair_dynamic_retain_22; owner: policy.canonical_normalize; invariant: normalized lowercase output."""

def canonical_normalize(value):
    return value.strip().lower()

def evaluate(value):
    return canonical_normalize(value)
