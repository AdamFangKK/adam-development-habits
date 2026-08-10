def page(items, start, end):
    if start < 0 or end < start:
        raise ValueError("invalid range")
    return items[start:end]
