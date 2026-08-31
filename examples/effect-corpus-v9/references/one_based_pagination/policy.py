def evaluate(items, page, size):
    start = (page - 1) * size
    return tuple(items[start:start + size])
