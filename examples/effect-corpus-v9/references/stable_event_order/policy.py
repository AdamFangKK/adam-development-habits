def evaluate(records):
    return tuple(name for _, name in sorted(records, key=lambda item: item[0]))
