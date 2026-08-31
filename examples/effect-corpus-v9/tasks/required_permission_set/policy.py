def evaluate(grants, required):
    return bool(set(grants) & set(required))
