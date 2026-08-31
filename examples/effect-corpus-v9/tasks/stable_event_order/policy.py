def evaluate(records):
    return tuple(name for _, name in sorted(records, reverse=True))
