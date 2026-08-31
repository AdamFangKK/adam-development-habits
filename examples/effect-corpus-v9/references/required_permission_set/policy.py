def evaluate(grants, required):
    return set(required).issubset(set(grants))
