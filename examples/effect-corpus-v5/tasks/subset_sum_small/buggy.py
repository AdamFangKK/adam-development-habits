def subset_sum(capacity, items):
    return any(sum(items[index] for index in range(len(items)) if mask & (1 << index)) == capacity - 1 for mask in range(1 << len(items)))
