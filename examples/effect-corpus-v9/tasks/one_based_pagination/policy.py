def evaluate(items, page, size):
    start = page * size
    return tuple(items[start:start + size])
